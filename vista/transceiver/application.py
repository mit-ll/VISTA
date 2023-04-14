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

import asyncio

from concurrent.futures import Executor, ThreadPoolExecutor
from typing import Mapping, Tuple, List, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import InitVar, dataclass
from asyncio import Queue, sleep, get_running_loop
from uuid import UUID
from abc import ABC, abstractmethod

from ..models.api import LoadSet, PublicKey
from ..models.domain import Message, StateUpdate, Token, ValidationError as DomainValidationError
from ..crypto import pks, ibs
from ..settings import settings
from . import logger, NavSource, RandomNavSource

class ValidationError(Exception):
    pass

@dataclass
class MessageKey:
    kid: int
    nbf: datetime
    exp: datetime
    public_key: ibs.PublicKey = None
    value: InitVar[PublicKey] = None

    def __post_init__(self, value):
      if self.public_key is None:
        if value is None:
          raise ValueError("must provide key or value")
        self.public_key = ibs.PublicKey.parse_obj(value)

@dataclass
class SigningKey:
    kid: int
    nbf: datetime
    exp: datetime
    key_group: ibs.IdentityKeyGroup = None
    gufi: InitVar[UUID] = None
    public_key: InitVar[PublicKey] = None
    value: InitVar[Tuple[str, str]] = None

    def __post_init__(self, gufi, public_key, value):
      if self.key_group is None:
        if None in (public_key, value, gufi):
          raise ValueError("must provide either key_group or all of gufi, public_key and value (private_key)")
        self.key_group = ibs.IdentityKeyGroup(
          identity = str(gufi),
          public_key = public_key,
          secret_key = value)

@dataclass
class TokenKey:
    kid: int
    nbf: datetime
    exp: datetime
    public_key: pks._PublicKey = None
    value: InitVar[str] = None

    def __post_init__(self, value):
      if self.public_key is None:
        if value is None:
          raise ValueError("must provide key or value")
        self.public_key = pks.deserialize_public_key(value)

class Application(ABC):
  def __init__(self, receive_queue:Queue, transmit_queue:Queue, loadset: Optional[LoadSet] = None, nav_src: Optional[NavSource] = None) -> None:
    self.receive_queue = receive_queue
    self.transmit_queue = transmit_queue

  @abstractmethod
  async def start(self):
    pass

class BlackHat(Application):

  def __init__(self, receive_queue: Queue, transmit_queue: Queue, loadset: LoadSet) -> None:
     
    self.token_keys = {key.kid: TokenKey(**key.dict()) for key in loadset.token_keys}
    self.message_keys = {key.kid: MessageKey(**key.dict()) for key in loadset.message_keys}

    super().__init__(receive_queue, transmit_queue)

  async def start(self):
    with ThreadPoolExecutor(settings.num_threads, "transceiver_application") as pool:
      await asyncio.gather(self.consume(pool))

  async def consume(self, pool: Executor):
    loop = get_running_loop()
    while True:
      tomr, data = await self.receive_queue.get()
      loop.run_in_executor(pool, BlackHat.receive, self, tomr, data)

  def receive(self, time: datetime, data: bytes) -> None:       
      msg = Message.unpack(data)
      logger.info(f"Received message from {msg.token.payload.gufi}")
      pos = (msg.payload.lon_deg, msg.payload.lat_deg)   
      try:
          Baseline.validate_msg(self.message_keys, self.token_keys, msg, time, pos)
      except (ValidationError, DomainValidationError) as err:
          logger.warn(f"Message validation FAILED: {err}.  Not using for replay")
      else:
          nav_src = RandomNavSource(msg.token.payload.bbox)
          msg.payload = nav_src.get_state(datetime.utcfromtimestamp(msg.payload.toa_utc))
          self.transmit_queue.put_nowait(msg.pack())

class Baseline(Application):

    def __init__(self, receive_queue:Queue, transmit_queue:Queue, loadset:LoadSet, nav_src:NavSource, broadcast_period:timedelta = timedelta(seconds = settings.broadcast_period_secs)) -> None:

      super().__init__(receive_queue, transmit_queue)

      self.nav_src = nav_src
      self.broadcast_period = broadcast_period
      self.gufi = loadset.gufi
      self.tokens = [Token.unpack(token.value) for token in loadset.tokens]
      self.token_keys = {key.kid: TokenKey(**key.dict()) for key in loadset.token_keys}
      self.message_keys = {key.kid: MessageKey(**key.dict()) for key in loadset.message_keys}
    
      self.signing_keys = []
      for signing_key in loadset.signing_keys:
        try:
          message_key = self.message_keys[signing_key.kid]
        except KeyError as exc:
          raise ValueError("No message key found for signing key") from exc
        self.signing_keys.append(
          SigningKey( 
            **signing_key.dict(),
            nbf = message_key.nbf,
            exp = message_key.exp,
            public_key = message_key.public_key,
            gufi = self.gufi            
          )
        )

    async def start(self):
      with ThreadPoolExecutor(settings.num_threads, "transceiver_application") as pool:
        await asyncio.gather(self.produce(pool), self.consume(pool))

    async def produce(self, pool: Executor):
      loop = get_running_loop()
      while True:
        toa = datetime.now(tz=timezone.utc)
        start_time = loop.time()
        payload = self.nav_src.get_state(toa)
        squitter = await loop.run_in_executor(pool, Baseline.assemble_msg, self.signing_keys, self.tokens, payload)
        try:
          self.transmit_queue.put_nowait(squitter.pack())
        except asyncio.QueueFull:
              logger.critical("transmit queue full - message dropped")
        delta = loop.time() - start_time
        delay = max(0, self.broadcast_period.total_seconds() - delta)
        if delay == 0:
          logger.critical("squitter producer slipping!")
        await sleep(delay)

    async def consume(self, pool: Executor):
      loop = get_running_loop()
      while True:
        tomr, data = await self.receive_queue.get()
        loop.run_in_executor(pool, Baseline.receive, self, tomr, data)

    def receive(self, time: datetime, data: bytes) -> None:       
        msg = Message.unpack(data)

        if msg.token.payload.gufi == self.gufi:
          logger.debug(f"ignoring message from self")
          return

        logger.info(f"Received message from {msg.token.payload.gufi}")
        
        own_state = self.nav_src.get_state(time)
        pos = (own_state.lon_deg, own_state.lat_deg)

        try:
            Baseline.validate_msg(self.message_keys, self.token_keys, msg, time, pos)
        except (ValidationError, DomainValidationError) as err:
            logger.warn(f"Message validation FAILED: {err}")
        else:
            logger.debug(msg.json())

    @staticmethod
    def choose_token(tokens: List[Token]) -> Token:
        now = datetime.now(tz=timezone.utc)
        for token in tokens:
            if token.payload.exp > now and token.payload.nbf < now:
                return token
        raise ValueError("no valid token found in loadset")

    @staticmethod
    def choose_signing_key(keys: List[SigningKey]) -> SigningKey:
        now = datetime.now(tz=timezone.utc)
        for key in keys:
            if key.exp > now and key.nbf < now:
                return key
        raise ValueError("no valid signing key found in loadset")

    @classmethod
    def assemble_msg(cls, signing_keys: List[SigningKey], tokens: List[Token], payload: StateUpdate) -> Message:

        signing_key = cls.choose_signing_key(signing_keys)
        token = cls.choose_token(tokens)   
        signature = ibs.sign(payload.pack(), signing_key.key_group)

        return Message(
            payload = payload,
            token = token,
            kid = signing_key.kid,
            signature = signature
        )

    @staticmethod
    def validate_msg(message_keys: Mapping[int, MessageKey], token_keys:Mapping[int, TokenKey], msg: Message, time: datetime, loc: Tuple) -> None:
        try:
            message_key = message_keys[msg.kid]
        except KeyError:
            raise ValidationError(f"message key {msg.kid} not found in load set")
        if time > message_key.exp:
            raise ValidationError(f"message key expired")
        if time < message_key.nbf:
            raise ValidationError(f"message not yet valid")

        try:
            token_key = token_keys[msg.token.kid]
        except KeyError:
            raise ValidationError(f"token key {msg.token.kid} not found in load set")
        if time > token_key.exp:
            raise ValidationError(f"token key expired")
        if time < token_key.nbf:
            raise ValidationError(f"token key not yet valid")

        msg.validate_(message_key.public_key, token_key.public_key, time, loc)
