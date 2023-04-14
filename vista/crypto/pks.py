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

from typing import Tuple, Optional, Union
from base64 import standard_b64decode, standard_b64encode

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as PrivateKey, Ed25519PublicKey as PublicKey
from cryptography.hazmat.backends.openssl.ed25519 import _Ed25519PrivateKey as _PrivateKey, _Ed25519PublicKey as _PublicKey
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption

from pydantic import BaseModel, validator

def key_as_bytes(key: Union[_PublicKey, _PrivateKey]) -> bytes:
    if isinstance(key, _PublicKey):
        return key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    elif isinstance(key, _PrivateKey):
        return key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    else:
        raise TypeError()

def key_as_str(key: Union[_PublicKey, _PrivateKey]) -> bytes:
    return standard_b64encode(key_as_bytes(key))

def deserialize_public_key(v) -> _PublicKey:
    if isinstance(v, _PublicKey):
        return v
    elif isinstance(v, bytes):
        try:
            return PublicKey.from_public_bytes(v)
        except Exception as exc:
            raise ValueError from exc
    elif isinstance(v, str):
        return deserialize_public_key(standard_b64decode(v))
    else:
        raise TypeError(f"expected str, bytes, or PublicKey, but received {type(v).__name__}")

def deserialize_private_key(v) -> _PrivateKey:
    if isinstance(v, _PrivateKey):
        return v
    elif isinstance(v, bytes):
        try:
            return PrivateKey.from_private_bytes(v)
        except Exception as exc:
            raise ValueError from exc
    elif isinstance(v, str):
        return deserialize_private_key(standard_b64decode(v))
    else:
        raise TypeError(f"expected str, bytes, or Private, but received {type(v).__name__}")

class KeyGroup(BaseModel):
    public_key: _PublicKey
    private_key: Optional[_PrivateKey]

    _public_key_validator = validator("public_key", pre=True)(deserialize_public_key)
    _private_key_validator = validator("private_key", pre=True)(deserialize_private_key)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            _PublicKey: key_as_str,
            _PrivateKey: key_as_str
        }

def generate_keys() -> KeyGroup:
    private_key = PrivateKey.generate()
    public_key = private_key.public_key()
    return KeyGroup(public_key = public_key, private_key = private_key)

def sign(msg: bytes, private_key: PrivateKey) -> bytes:
    return private_key.sign(msg)

def verify(public_key: PublicKey, msg: bytes, signature: bytes) -> bool:
    try:
        public_key.verify(signature, msg)
    except InvalidSignature:
        return False
    else:
        return True
