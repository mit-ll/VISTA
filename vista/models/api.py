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

from datetime import datetime
import json
from typing import Callable, Tuple, List, Union
from base64 import standard_b64encode

from pydantic import BaseModel, UUID4, EmailStr, validator, Field
from sqlalchemy.sql.expression import true

def b64encode_bytes(value: Union[str, bytes]) -> str:
    if isinstance(value, bytes):
        return standard_b64encode(value)
    else:
        return value

def _str_validator(*args) -> Callable:
    return validator(*args, pre=True, each_item=True, allow_reuse=True)(b64encode_bytes)

class Operator(BaseModel):
    name   : str
    email  : EmailStr
    address: str
    phone  : str

    class Config:
        orm_mode = true

class AuthorizationBase(BaseModel):
    gufi: UUID4
    nbf:  datetime
    exp:  datetime
    bbox: Tuple[float, float,float, float]

    @validator("exp")
    @classmethod
    def validate_exp_gt_nbf(cls, exp, values):
        if not exp > values["nbf"]:
            raise ValueError("Expiration must be after NBF")
        return exp

    @validator("bbox")
    @classmethod
    def validate_bbox(cls, bbox):
        for lon, lat in bbox[2:], bbox[:2]:
            if abs(lon) > 180:
                raise ValueError("Longitude out of range")
            if abs(lat) > 90:
                raise ValueError("Latitude out of range")
        return bbox

    class Config:
        orm_mode = true

class AuthorizationRequest(AuthorizationBase):
    pass

class AuthorizationDetails(AuthorizationBase):
    granted: datetime

class AuthorizationPrivledgedDetails(AuthorizationDetails):
    operator: Operator

class Token(BaseModel):
    nbf:   datetime
    exp:   datetime
    value: str

    _validate_value = _str_validator('value')

    class Config:
        orm_mode = true

class TokenKey(BaseModel):
    kid:   int = Field(alias="pk")
    nbf:   datetime
    exp:   datetime
    value: str = Field(alias="public_key")

    _validate_value = _str_validator('value')

    class Config:
        orm_mode = true
        allow_population_by_field_name = True

class PublicKey(BaseModel): 
    g1 : str
    g2 : str
    A  : str
    u1t: str
    u2t: str
    u  : List[str]
    u1b: str
    u2b: str
    ub : List[str]
    z  : int
    l  : int

class MessageKey(BaseModel):
    kid:   int = Field(alias="pk")
    nbf:   datetime
    exp:   datetime
    value: PublicKey = Field(alias="public_key")

    @validator("value", pre=True)
    def deserialize_public_key(value):
        if isinstance(value, str):
            return PublicKey.parse_raw(value)
        else:
            return value

    class Config:
        orm_mode = true
        allow_population_by_field_name = True

class SigningKey(BaseModel):
    kid:   int = Field(alias="root_key_pk")
    value: Tuple[str, str] = Field(alias="private_key")

    @validator("value", pre=True)
    def deserialize_public_key(value):
        if isinstance(value, str):
            return json.loads(value)
        else:
            return value

    class Config:
        orm_mode = true
        allow_population_by_field_name = True

class LoadSet(BaseModel): 
    gufi         : UUID4
    tokens       : List[Token]
    token_keys   : List[TokenKey]
    signing_keys : List[SigningKey]
    message_keys : List[MessageKey]
