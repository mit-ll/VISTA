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

import datetime
import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, LargeBinary, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID


Base = declarative_base()

class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.

    Sourced from SQLAlchemy documentation:
    https://docs.sqlalchemy.org/en/13/core/custom_types.html#backend-agnostic-guid-type

    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                # hexstring
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value


class TZDateTime(TypeDecorator):
    """Datatype that convert timezone aware timestamps into timezone naive and back again

    Sourced from SQLAlchemy documentation:
    https://docs.sqlalchemy.org/en/13/core/custom_types.html#store-timezone-aware-timestamps-as-timezone-naive-utc

    """
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if not value.tzinfo:
                raise TypeError("tzinfo is required")
            value = value.astimezone(datetime.timezone.utc).replace(
                tzinfo=None
            )
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return value

class Authorization(Base):
    __tablename__ = "authorizations"

    pk          = Column(Integer, primary_key=True, index=True)
    operator_pk = Column(Integer, ForeignKey("operators.pk"), nullable = False)

    gufi        = Column(GUID, nullable = False, unique=True)
    nbf         = Column(TZDateTime, nullable = False)
    exp         = Column(TZDateTime, nullable = False)
    bbox        = Column(JSON, nullable = False)
    granted     = Column(TZDateTime, nullable = False)

    operator = relationship("Operator", backref="authorizations")

class Token(Base):
    __tablename__ = "tokens"

    pk               = Column(Integer, primary_key=True, index=True)
    authorization_pk = Column(Integer, ForeignKey("authorizations.pk"), nullable = False)
    key_pk           = Column(Integer, ForeignKey("token_keys.pk"), nullable = False)

    nbf              = Column(TZDateTime, nullable = False)
    exp              = Column(TZDateTime, nullable = False)
    value            = Column(LargeBinary, nullable=False)
    
    authorization = relationship("Authorization", backref="tokens")
    key           = relationship("TokenKey", backref="tokens")


class TokenKey(Base):
    __tablename__ = "token_keys"

    pk         = Column(Integer, primary_key=True, index=True)

    nbf        = Column(TZDateTime, nullable = False)
    exp        = Column(TZDateTime, nullable = False)
    public_key = Column(LargeBinary, nullable = False)
    secret_key = Column(LargeBinary, nullable = False)

class SigningKey(Base):
    __tablename__ = "signing_keys"

    pk               = Column(Integer, primary_key=True, index=True)
    root_key_pk      = Column(Integer, ForeignKey("root_keys.pk"), nullable = False)
    authorization_pk = Column(Integer, ForeignKey("authorizations.pk"), nullable = False)

    private_key      = Column(JSON, nullable=False)

    root_key      = relationship("RootKey", backref="signing_keys")
    authorization = relationship("Authorization", backref = "signing_keys")

class RootKey(Base):
    __tablename__ = "root_keys"

    pk         = Column(Integer, primary_key=True, index=True)

    nbf        = Column(TZDateTime, nullable = False)
    exp        = Column(TZDateTime, nullable = False)
    public_key = Column(JSON, nullable=False)
    secret_key = Column(LargeBinary, nullable=False)

class Operator(Base):
    __tablename__ = "operators"

    pk      = Column(Integer, primary_key=True, index=True)
    
    name    = Column(String, index=True)
    email   = Column(String)
    address = Column(String)
    phone   = Column(String)

