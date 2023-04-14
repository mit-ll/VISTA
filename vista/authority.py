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

from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy.orm import Session

from .models import domain, database, api
from .crypto import pks, ibs
from .settings import settings

KEY_INTERVAL = timedelta(minutes = settings.key_rotation_mins)
KEY_EXP_BUFFER = timedelta(milliseconds = settings.key_expiration_buffer_ms)

def generate_authorization(db: Session, request: api.AuthorizationRequest, operator: database.Operator) -> database.Authorization:
     
    def generate_token(key: database.TokenKey) -> database.Token:
        
        private_key = pks.deserialize_private_key(key.secret_key)
        
        payload = domain.TokenPayload(
            gufi = request.gufi,
            nbf = max(request.nbf, key.nbf),
            exp = min(request.exp, key.exp),
            bbox = request.bbox
        )
        packed_payload = payload.pack()
        signature = pks.sign(packed_payload, private_key)

        packed_value = domain.Token(
            payload = payload,
            kid = key.pk,
            signature = signature
        ).pack()

        return database.Token(
            nbf = payload.nbf,
            exp = payload.exp,
            value = packed_value,
            key = key
        )

    def generate_signing_key(key: database.RootKey) -> database.SigningKey:

        root_key = ibs.KeyGroup(
            public_key = ibs.PublicKey.parse_raw(key.public_key),
            secret_key = key.secret_key
        )
        identity_key = ibs.generate_identity_key(str(request.gufi), root_key)
        
        return database.SigningKey(
            private_key = ibs.key_as_str(identity_key.secret_key),
            root_key = key
        )

    return database.Authorization(
         gufi = request.gufi,
         nbf = request.nbf,
         exp = request.exp,
         bbox = request.bbox,
         operator = operator,
         granted = datetime.now(tz=timezone.utc),
         tokens = [generate_token(key) for key in choose_token_keys(db, request.nbf, request.exp)],
         signing_keys = [generate_signing_key(key) for key in choose_root_keys(db, request.nbf, request.exp)]
     )

def choose_token_keys(db: Session, start: datetime, end: datetime) -> List[database.TokenKey]:    
    token_keys = db.query(database.TokenKey).filter(database.TokenKey.exp > start, database.TokenKey.nbf < end).order_by(database.TokenKey.nbf.asc()).all()
    if not token_keys:
        raise ValueError("no token keys for time range")
    if token_keys[-1].exp < end:
        raise ValueError("token keys do not cover time range")
    return token_keys


def choose_root_keys(db: Session, start: datetime, end: datetime) -> List[database.RootKey]:   
    root_keys = db.query(database.RootKey).filter(database.RootKey.exp > start, database.RootKey.nbf < end).order_by(database.RootKey.nbf.asc()).all()
    if not root_keys:
        raise ValueError("no root keys for time range")
    if root_keys[-1].exp < end:
        raise ValueError("root keys do not cover time range")
    return root_keys

def add_token_keys(db: Session, end: datetime) -> None:

    last = db.query(database.TokenKey.nbf, database.TokenKey.exp).order_by(database.TokenKey.exp.desc()).first()

    if last is None: 
        start = datetime.now(tz=timezone.utc)
        start = start - (start - datetime.min.replace(tzinfo=timezone.utc)) % KEY_INTERVAL
        token_keys = generate_token_keys(start, end)
    elif last.exp < end:
        token_keys = generate_token_keys(last.nbf + KEY_INTERVAL, end)
    else:
        return

    db.add_all(token_keys)
    db.commit()

def add_root_keys(db: Session, end: datetime) -> None:

    last = db.query(database.RootKey.nbf, database.RootKey.exp).order_by(database.RootKey.exp.desc()).first()

    if last is None: 
        start = datetime.now(tz=timezone.utc)
        start = start - (start - datetime.min.replace(tzinfo=timezone.utc)) % KEY_INTERVAL
        root_keys = generate_root_keys(start, end)
    elif last.exp < end:
        root_keys = generate_root_keys(last.nbf + KEY_INTERVAL, end)
    else:
        return

    db.add_all(root_keys)
    db.commit()

def generate_root_keys(start: datetime, end: datetime) -> List[database.RootKey]:
    if not end > start:
        raise ValueError("start must be before end")

    root_keys = []
    for i in range(1 + int((end-start)/KEY_INTERVAL)):
        key_group = ibs.generate_root_key()
        root_key = database.RootKey(
            nbf = start + i*KEY_INTERVAL,
            exp = start + (i+1)*KEY_INTERVAL + KEY_EXP_BUFFER,
            public_key = key_group.public_key.json(),
            secret_key = ibs.key_as_bytes(key_group.secret_key)
        )
        root_keys.append(root_key)

    return root_keys
    
def generate_token_keys(start: datetime, end: datetime) -> List[database.TokenKey]:
    if not end > start:
        raise ValueError("start must be before end")

    token_keys = []
    for i in range(1 + int((end-start)/KEY_INTERVAL)):
        key_group = pks.generate_keys()
        token_key = database.TokenKey(
            nbf = start + i*KEY_INTERVAL,
            exp = start + (i+1)*KEY_INTERVAL + KEY_EXP_BUFFER,
            public_key = pks.key_as_bytes(key_group.public_key),
            secret_key = pks.key_as_bytes(key_group.private_key)
        )
        token_keys.append(token_key)

    return token_keys
    