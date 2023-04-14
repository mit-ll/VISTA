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

import random

from datetime import datetime, timedelta
from uuid import uuid4
from typing import TypeVar
from os import urandom
from pytest import approx
from base64 import standard_b64encode

from vista.models.domain import DomainBaseModel, StateUpdate, TokenPayload, Token, Message
from vista.crypto import ibs, pks
from vista.settings import settings

from charm.toolbox.pairinggroup import G1

T = TypeVar('T', bound=DomainBaseModel)
def pack_unpack(model: T) -> T:
    return type(model).unpack(model.pack())

def json_serde(model: T) -> T:
    return type(model).parse_raw(model.json())

TIME_RESOLUTION = timedelta(milliseconds=settings.time_resolution_ms)
MIN_DATETIME = datetime.fromisoformat(settings.min_datetime)

token_payload = TokenPayload(
    gufi = uuid4(),
    nbf = MIN_DATETIME,
    exp = MIN_DATETIME + TIME_RESOLUTION,
    bbox = (-40,30,-30,40)
)

token = Token(
    payload = token_payload,
    kid = 0, 
    signature = urandom(64)
)

state_update = StateUpdate.parse_obj({
    'lat_deg'     : random.uniform(-90, 90),
    'lon_deg'     : random.uniform(-180, 180),
    'alt_hae_ft'  : random.uniform(0, 10000),
    'vel_ew_fps'  : random.uniform(-250,250),
    'vel_ns_fps'  : random.uniform(-250,250),
    'vel_vert_fps': random.uniform(-50,50),
    'toa_utc'     : datetime.utcnow().timestamp()
})

msg_signature = ibs.Signature(**{k:v for k,v in zip(['S1', 'S2', 'S3'], ibs.pairing_group.random(G1, 3))})

message = Message(
    token = token,
    kid = 0,
    payload = state_update,
    signature = msg_signature
)


def test_pack_unpack():
    assert Token.unpack(standard_b64encode(token.pack()).decode('utf-8')) == token
    unpacked_msg = pack_unpack(message)
    assert unpacked_msg.token == token
    assert unpacked_msg.kid == 0
    assert unpacked_msg.payload.dict() == approx(state_update.dict())
    assert unpacked_msg.signature == msg_signature

def test_json_serde():
    parsed_msg = json_serde(message)
    assert parsed_msg.token == token
    assert parsed_msg.kid == 0
    assert parsed_msg.payload.dict() == approx(state_update.dict())
    assert parsed_msg.signature == msg_signature