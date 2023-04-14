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

from uuid import uuid4
from itertools import product
from typing import TypeVar

from pydantic import BaseModel

from vista.crypto import ibs, pks

T = TypeVar('T', bound=BaseModel)
def json_serde(input: T) -> T:
    return type(input).parse_raw(input.json())

def binary_permutations(length: int) -> str:
    return [''.join(x) for x in product('01', repeat=length)]

def test_ibs():

    # 1. generate signatures for each of 8 combinations of ID string, msg, and root key
    # 2. pass each element through JSON serialization / deserialization
    # 3. check that the correct set of ID string, msg, and root key validates each signature
    # 4. check that each invalid combination of ID string, msg, and root key fails validation for each signature
    
    IDs = {
        '0': str(uuid4()),
        '1': "janedoe@email.com"
    }
    
    # msgs of both bytes and str types
    msgs = {
        '0': b"\x4d\x48\xac\xe0\x88\xe9\x07\x16\xc5\x12\x19\x76\x5c\x0d\x36\x78\xfa\x6f\x31\x1d\x6d\x89\xe4\xc8\x15\x56\xdf\x58\xb6\xf0\x8d\x18",
        '1': "this is a message!"
    }
    
    root_keys = {k: json_serde(ibs.generate_root_key()) for k in binary_permutations(1)}
    identity_keys = {k: json_serde(ibs.generate_identity_key(IDs[k[0]], root_keys[k[1]])) for k in binary_permutations(2)}    
    signatures = {k: json_serde(ibs.sign(msgs[k[0]], identity_keys[k[1:]])) for k in binary_permutations(3)}


    for signed_combination, signature in signatures.items():
        for test_combination in binary_permutations(3):
            verified = ibs.verify(root_keys[test_combination[2]].public_key, IDs[test_combination[1]], msgs[test_combination[0]], signature)
            if test_combination == signed_combination:
                assert verified
            else:
                assert not verified


def test_pks():

    # 1. generate signatures for each of 4 combinations of ID string and key set
    # 2. pass key set through JSON serialization / deserialization
    # 3. check that the correct set of msg and public key validates each signature
    # 4. check that each invalid combination of msg, and public key fails validation for each signature

    key_groups = {k: json_serde(pks.generate_keys()) for k in binary_permutations(1)}    
    msgs = {
        '0': b"\x4d\x48\xac\xe0\x88\xe9\x07\x16\xc5\x12\x19\x76\x5c\x0d\x36\x78\xfa\x6f\x31\x1d\x6d\x89\xe4\xc8\x15\x56\xdf\x58\xb6\xf0\x8d\x18",
        '1': b"this is a message!"
    }
    signatures = {k: pks.sign(msgs[k[0]], key_groups[k[1]].private_key) for k in binary_permutations(2)}
    for signed_combination, signature in signatures.items():
        for test_combination in binary_permutations(2):
            verified = pks.verify(key_groups[test_combination[1]].public_key, msgs[test_combination[0]], signature)
            if test_combination == signed_combination:
                assert verified
            else:
                assert not verified