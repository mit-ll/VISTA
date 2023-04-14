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
from typing import List, Union

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, defer
from sqlalchemy.orm.exc import NoResultFound
from fastapi import Depends, FastAPI, HTTPException
from pydantic.types import UUID4
from pydantic import UUID4

from .settings import settings
from .models import database, api
from . import authority

engine = create_engine(settings.db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
database.Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def operator_from_request(db: Session = Depends(get_db)) -> database.Operator:
    operator = db.query(database.Operator).get(1)
    if not operator:
        operator = database.Operator(
            name = "jane doe",
            email = "jane.doe@future.v2v",
            address = "99 foo bar rd",
            phone = "999-999-9999"
        )
        db.add(operator)
        db.commit()
    return operator
    

@app.get("/operators", response_model=List[api.Operator])
def get_operators(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    operators = db.query(database.Operator).offset(skip).limit(limit).all()
    return [api.Operator.from_orm(operator) for operator in operators]

@app.get("/operator/{id}", response_model=api.Operator)
def get_operator(id: int, db: Session = Depends(get_db)):
    operator = db.query(database.Operator).get(id)
    if operator is None:
        raise HTTPException(404, "Operator not found")
    return api.Operator.from_orm(operator)

@app.get("/authorizations", response_model=List[Union[api.AuthorizationPrivledgedDetails, api.AuthorizationDetails]])
def get_authorizations(skip: int = 0, limit: int = 100, privledged: bool = False, db: Session = Depends(get_db)):
    authorizations = db.query(database.Authorization).offset(skip).limit(limit).all()
    if privledged:
        return [api.AuthorizationPrivledgedDetails.from_orm(authorization) for authorization in authorizations]    
    else:
        return [api.AuthorizationDetails.from_orm(authorization) for authorization in authorizations]

@app.get("/authorization/{gufi}", response_model=Union[api.AuthorizationPrivledgedDetails, api.AuthorizationDetails])
def get_authorization(gufi: UUID4, privledged: bool = False, db: Session = Depends(get_db)):
    try:
        authorization = db.query(database.Authorization).filter_by(gufi = gufi).one()
    except NoResultFound:
        raise HTTPException(404, "Authorization not found")
    if privledged:
        return api.AuthorizationPrivledgedDetails.from_orm(authorization)
    else:
        return api.AuthorizationDetails.from_orm(authorization)

@app.post("/authorization", response_model=api.LoadSet)
def post_authorization(request: api.AuthorizationRequest, operator: database.Operator = Depends(operator_from_request), db: Session = Depends(get_db)):

    if db.query(database.Authorization).filter(database.Authorization.gufi == request.gufi).scalar() is not None:
        raise HTTPException(409, "authorization for gufi already exists")

    authority.add_root_keys(db, request.exp)
    authority.add_token_keys(db, request.exp)

    authorization = authority.generate_authorization(db, request, operator)
    db.add(authorization)
    db.commit()

    return get_loadset(request.gufi, db)

@app.get("/token_keys", response_model=List[api.TokenKey], response_model_by_alias=False)
def get_token_keys(skip: int = 0, limit: int = 100, nbf: datetime = None, exp: datetime = None, db: Session = Depends(get_db)):
    if None not in (nbf, exp):
        token_keys = db.query(database.TokenKey).filter(database.TokenKey.exp > nbf, database.TokenKey.nbf < exp).offset(skip).limit(limit).all()
    elif nbf is not None:
        token_keys = db.query(database.TokenKey).filter(database.TokenKey.exp > nbf).offset(skip).limit(limit).all()
    elif exp is not None:
        token_keys = db.query(database.TokenKey).filter(database.TokenKey.nbf < exp).offset(skip).limit(limit).all()
    else:
        token_keys = db.query(database.TokenKey).offset(skip).limit(limit).all()
    return [api.TokenKey.from_orm(key) for key in token_keys]

@app.get("/token_key/{kid}", response_model=api.TokenKey, response_model_by_alias=False)
def get_token_key(kid: int, db: Session = Depends(get_db)):
    try:
        token_key = db.query(database.TokenKey).filter_by(pk = kid).one()
    except NoResultFound:
        raise HTTPException(404, "Key not found")
    return api.TokenKey.from_orm(token_key)

@app.get("/message_keys", response_model=List[api.MessageKey], response_model_by_alias=False)
def get_signatre_keys(skip: int = 0, limit: int = 100, nbf: datetime = None, exp: datetime = None, db: Session = Depends(get_db)):
    if None not in (nbf, exp):
        root_keys = db.query(database.RootKey).filter(database.RootKey.exp > nbf, database.RootKey.nbf < exp).offset(skip).limit(limit).all()
    elif nbf is not None:
        root_keys = db.query(database.RootKey).filter(database.RootKey.exp > nbf).offset(skip).limit(limit).all()
    elif exp is not None:
        root_keys = db.query(database.RootKey).filter(database.RootKey.nbf < exp).offset(skip).limit(limit).all()
    else:
        root_keys = db.query(database.RootKey).offset(skip).limit(limit).all()
    return [api.MessageKey.from_orm(key) for key in root_keys]

@app.get("/message_key/{kid}", response_model=api.MessageKey, response_model_by_alias=False)
def get_signature_key(kid: int, db: Session = Depends(get_db)):
    try:
        root_key = db.query(database.RootKey).filter_by(pk = kid).one()
    except NoResultFound:
        raise HTTPException(404, "Key not found")
    return api.MessageKey.from_orm(root_key)

@app.get("/loadset/{gufi}", response_model=api.LoadSet, response_model_by_alias=False)
def get_loadset(gufi: UUID4, db: Session = Depends(get_db)):

    try:
        authorization = db.query(database.Authorization).filter_by(gufi = gufi).one()
    except NoResultFound:
        raise HTTPException(404, "Authorization not found")

    token_keys = db.query(database.TokenKey).filter(database.TokenKey.exp > authorization.nbf, database.TokenKey.nbf < authorization.exp).all()
    root_keys = db.query(database.RootKey).filter(database.RootKey.exp > authorization.nbf, database.RootKey.nbf < authorization.exp).all()

    return api.LoadSet(
        gufi = gufi,
        tokens = [api.Token.from_orm(token) for token in authorization.tokens],
        token_keys = [api.TokenKey.from_orm(key) for key in token_keys],
        message_keys = [api.MessageKey.from_orm(key) for key in root_keys],
        signing_keys = [api.SigningKey.from_orm(key) for key in authorization.signing_keys]
    )
