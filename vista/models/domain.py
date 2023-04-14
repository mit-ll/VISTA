# DISTRIBUTION STATEMENT A. Approved for public release. Distribution is unlimited.
#
# This material is based upon work supported by the Federal Aviation Administration under Air Force Contract No. FA8702-15-D-0001. 
# Any opinions, findings, conclusions or recommendations expressed in this material are those of the author(s) 
# and do not necessarily reflect the views of the Federal Aviation Administration.
#
# © 2023 Massachusetts Institute of Technology.
#
# Subject to FAR52.227-11 Patent Rights - Ownership by the contractor (May 2014)
#
# The software/firmware is provided to you on an As-Is basis
#
# Delivered to the U.S. Government with Unlimited Rights, as defined in DFARS Part 252.227-7013 or 7014 (Feb 2014). 
# Notwithstanding any copyright notice, U.S. Government rights in this work are defined by DFARS 252.227-7013 
# or DFARS 252.227-7014 as detailed above. Use of this work other than as specifically authorized by the 
# U.S. Government may violate any copyrights that exist in this work.

import struct

from datetime import datetime
from typing import Tuple, Union, Callable
from base64 import standard_b64decode, standard_b64encode
from pydantic import BaseModel, UUID4, validator

from ..crypto import pks, ibs
from ..utils import bbox_includes, encode_datetime_as_int, decode_datetime_from_int, ROUND_CEILING, ROUND_FLOOR

def b64decode_str(value: Union[str, bytes]) -> bytes:
    if isinstance(value, str):
        return standard_b64decode(value)
    else:
        return value

def _bytes_validator(*args) -> Callable:
    return validator(*args, pre=True, each_item=True, allow_reuse=True)(b64decode_str)

class ValidationError(Exception):
    pass

class DomainBaseModel(BaseModel):
    _struct_format: str

    @classmethod
    def unpack(cls, data:bytes):
        values = struct.unpack(cls._struct_format, data)
        return cls.parse_obj(dict(zip(cls.__fields__, values)))

    def pack(self) -> bytes:
        return struct.pack(self._struct_format, 
        *self.dict().values())

    class Config:
        json_encoders = {
            bytes: lambda v: standard_b64encode(v).decode('utf-8'),
            ibs.PairingElement: lambda v: ibs.pairing_group.serialize(v).decode('utf-8')
        }

class TokenPayload(DomainBaseModel):
    gufi: UUID4   # 16s
    nbf : datetime # I
    exp : datetime # I
    bbox: Tuple[float, float, float, float] #4f

    _struct_format: str = '! 16s 2I 4f'

    def pack(self) -> bytes:
        return struct.pack(self._struct_format,
            self.gufi.bytes,
            encode_datetime_as_int(self.nbf, ROUND_FLOOR),
            encode_datetime_as_int(self.exp, ROUND_CEILING),
            *self.bbox
        )

    @classmethod
    def unpack(cls, data:bytes):
        values = struct.unpack(cls._struct_format, data)
        return cls(
            gufi = UUID4(bytes = values[0]),
            nbf = decode_datetime_from_int(values[1]),
            exp = decode_datetime_from_int(values[2]),
            bbox = tuple(values[3:])
        )

    def validate_(self, time: datetime, loc: Tuple):
        if time > self.exp:
            raise ValidationError("token expired")
        if time < self.nbf:
            raise ValidationError("token not yet valid")
        if not bbox_includes(self.bbox, loc):
            raise ValidationError("token spatial bounds exceeded")


class Token(DomainBaseModel):
    payload  : TokenPayload
    kid      : int
    signature: bytes

    _validate_signature = _bytes_validator('signature')

    _struct_format: str = '! 40s I 64s'

    def pack(self) -> bytes:
        return struct.pack(self._struct_format,
            self.payload.pack(),
            self.kid,
            self.signature
        )

    @classmethod
    def unpack(cls, data:Union[bytes, str]):
        if isinstance(data, str):
            data = standard_b64decode(data)
        values = struct.unpack(cls._struct_format, data)
        return cls(
            payload = TokenPayload.unpack(values[0]),
            kid = values[1],
            signature = values[2]
        )

    def validate_(self, token_key: pks._PublicKey, *args, **kwargs):
        self.payload.validate_(*args, **kwargs)
        if not pks.verify(token_key, self.payload.pack(), self.signature):
            raise ValidationError("token signature invalid")


class StateUpdate(DomainBaseModel):
    lat_deg     : float
    lon_deg     : float
    alt_hae_ft  : float
    vel_ew_fps  : float
    vel_ns_fps  : float
    vel_vert_fps: float
    toa_utc     : float

    _struct_format: str = '! 7f'

class Message(DomainBaseModel):
    token    : Token
    kid      : int
    payload  : StateUpdate
    signature: ibs.Signature

    _struct_format: str = '! 108s I 28s 21s 21s 21s'

    def pack(self) -> bytes:
        return struct.pack(self._struct_format,
            self.token.pack(),
            self.kid,
            self.payload.pack(),
            standard_b64decode(ibs.key_as_bytes(self.signature.S1)[2:]),
            standard_b64decode(ibs.key_as_bytes(self.signature.S2)[2:]),
            standard_b64decode(ibs.key_as_bytes(self.signature.S3)[2:])
        )

    @classmethod
    def unpack(cls, data:bytes):
        values = struct.unpack(cls._struct_format, data)
        return cls(
            token = Token.unpack(values[0]),
            kid = values[1],
            payload = StateUpdate.unpack(values[2]),
            signature = ibs.Signature(
                S1 = b'1:' + standard_b64encode(values[3]),
                S2 = b'1:' + standard_b64encode(values[4]),
                S3 = b'1:' + standard_b64encode(values[5])
            )
        )

    def validate_(self, message_key: ibs.PublicKey, *args, **kwargs):
        self.token.validate_(*args, **kwargs)
        if not ibs.verify(message_key, str(self.token.payload.gufi), self.payload.pack(), self.signature):
            raise ValidationError("message signature invalid")



