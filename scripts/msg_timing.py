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
import timeit

from datetime import datetime, timezone, timedelta
from uuid import uuid4

from vista.models.domain import StateUpdate, TokenPayload, Token, Message
from vista.crypto import ibs, pks
from vista.transceiver.application import TokenKey, MessageKey, Baseline, SigningKey


gufi = uuid4()
now = datetime.now(tz=timezone.utc)
loc = (0,0)
pos = {
    'lat_deg'     : random.uniform(-90, 90),
    'lon_deg'     : random.uniform(-180, 180),
    'alt_hae_ft'  : random.uniform(0, 10000),
    'vel_ew_fps'  : random.uniform(-250,250),
    'vel_ns_fps'  : random.uniform(-250,250),
    'vel_vert_fps': random.uniform(-50,50),
    'toa_utc'     : now.timestamp()
}

pks_root_key = pks.generate_keys()
ibs_root_key = ibs.generate_root_key()
ibs_key_group = ibs.generate_identity_key(str(gufi), ibs_root_key)

signing_keys = [SigningKey(
    kid = 0, 
    nbf = now - timedelta(minutes=1),
    exp = now + timedelta(minutes=1),
    key_group = ibs_key_group)]

token_payload = TokenPayload(
    gufi = gufi,
    nbf = now - timedelta(minutes=1),
    exp = now + timedelta(minutes=1),
    bbox = (0,0,0,0)
)
tokens = [Token(
    payload = token_payload,
    kid = 0,
    signature = pks.sign(token_payload.pack(), pks_root_key.private_key)
)]

repetitions = 10000
time = timeit.timeit('Baseline.assemble_msg(signing_keys, tokens, StateUpdate.parse_obj(pos)).pack()', globals=globals(), number=repetitions)
print(f"Avg message assembly time was {time/repetitions} seconds over {repetitions} repetitions ")


token_keys = {0: TokenKey(
    kid = 0,
    nbf = now - timedelta(minutes=1),
    exp = now + timedelta(minutes=1),
    public_key = pks_root_key.public_key
)}

message_keys = {0: MessageKey(
    kid = 0,
    nbf = now - timedelta(minutes=1),
    exp = now + timedelta(minutes=1),
    public_key = ibs_key_group.public_key
)}

packed_msg = Baseline.assemble_msg(signing_keys, tokens, StateUpdate.parse_obj(pos)).pack()

repetitions = 1000
time = timeit.timeit('Baseline.validate_msg(message_keys, token_keys, Message.unpack(packed_msg), now, loc)', globals=globals(), number=repetitions)
print(f"Avg message validation time was {time/repetitions} seconds over {repetitions} repetitions ")
