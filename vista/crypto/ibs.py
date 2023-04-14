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

from base64 import standard_b64encode
from typing import List, Tuple, Callable, Union
import json

from pydantic import BaseModel, validator

from charm.toolbox.pairinggroup import PairingGroup
from charm.core.math.pairing import pc_element as PairingElement
from charm.schemes.pksig.pksig_waters import WatersSig

pairing_group = PairingGroup('MNT159')
engine = WatersSig(pairing_group)
engine.setup(5)

def deserialize_pairing_element(v) -> PairingElement:
    if isinstance(v, PairingElement):
        return v
    elif isinstance(v, bytes):
        try:
            return pairing_group.deserialize(v)
        except Exception as exc:
            raise ValueError from exc
    elif isinstance(v, str):
        return deserialize_pairing_element(bytes(v, "utf-8"))
    else:
        raise TypeError(f"expected str, bytes, or PairingElement, but received {type(v).__name__}")

def _pairing_elements_validator(*args) -> Callable:
    return validator(*args, pre=True, each_item=True, allow_reuse=True)(deserialize_pairing_element)

class CryptoBaseModel(BaseModel):

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            PairingElement: pairing_group.serialize
        }

class PublicKey(CryptoBaseModel):
    g1: PairingElement
    g2: PairingElement
    A: PairingElement
    u1t: PairingElement
    u2t: PairingElement
    u: List[PairingElement]
    u1b: PairingElement
    u2b: PairingElement
    ub: List[PairingElement]
    z: int
    l: int

    _validate_pairing_elements = _pairing_elements_validator('g1', 'g2', 'A', 'u1t', 'u2t', 'u', 'u1b', 'u2b', 'ub')

class KeyGroup(CryptoBaseModel):
    public_key: PublicKey
    secret_key: PairingElement

    _validate_pairing_elements = _pairing_elements_validator('secret_key')

class IdentityKeyGroup(KeyGroup):
    identity: str
    secret_key: Tuple[PairingElement, PairingElement]

class Signature(CryptoBaseModel):
    S1: PairingElement
    S2: PairingElement
    S3: PairingElement

    _validate_pairing_elements = _pairing_elements_validator('S1', 'S2', 'S3')

def key_as_bytes(key: Union[PublicKey, PairingElement, Tuple[PairingElement, PairingElement]]) -> bytes:
    if isinstance(key, PublicKey):
        raise NotImplementedError()
    if isinstance(key, PairingElement):
        return pairing_group.serialize(key)
    elif isinstance(key, tuple):
        return tuple(pairing_group.serialize(elem) for elem in key)
    else:
        raise TypeError()

def key_as_str(key: Union[PublicKey, PairingElement, Tuple[PairingElement, PairingElement]]) -> str:
    if isinstance(key, PublicKey):
        raise NotImplementedError()
    if isinstance(key, PairingElement):
        return str(pairing_group.serialize(key), "utf-8")
    elif isinstance(key, tuple):
        return json.dumps(tuple(str(pairing_group.serialize(elem), "utf-8") for elem in key))
    else:
        raise TypeError()

def generate_root_key() -> KeyGroup:
    (public_key, secret_key) = engine.setup(5)
    return KeyGroup(public_key=public_key, secret_key = secret_key)

def generate_identity_key(id, root_key: KeyGroup) -> IdentityKeyGroup:
    secret_key = engine.keygen(root_key.public_key.dict(), root_key.secret_key, id)
    return IdentityKeyGroup(identity = id, public_key = root_key.public_key, secret_key = secret_key)

def sign(msg: Union[str, bytes], identity_key: IdentityKeyGroup) -> Signature:
    if isinstance(msg, bytes):
        msg = standard_b64encode(msg).decode('utf-8')
    signature = engine.sign(identity_key.public_key.dict(), identity_key.secret_key, msg)
    return Signature.parse_obj(signature)

def verify(root_public_key: PublicKey, id: str, msg: Union[str, bytes], signature: Signature) -> bool:
    if isinstance(msg, bytes):
        msg = standard_b64encode(msg).decode('utf-8')
    return engine.verify(root_public_key.dict(), id, msg, signature.dict())
