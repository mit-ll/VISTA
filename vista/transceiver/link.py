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
import socket
import struct

from typing import Tuple, Optional
from datetime import datetime, timezone
from asyncio import DatagramProtocol, transports, Future, Queue, get_running_loop
from abc import ABC, abstractmethod

from ..settings import settings

from . import logger

class Link(ABC):
  def __init__(self, receive_queue:Queue, transmit_queue:Queue) -> None:
    self.receive_queue = receive_queue
    self.transmit_queue = transmit_queue

  @abstractmethod
  async def start(self):
    pass

class IpMulticast(Link):

  class Protocol(DatagramProtocol):

    def __init__(self, recv_queue: Queue, completed: Future) -> None:
      self.msg_queue = recv_queue
      self.completed = completed
    
    def connection_made(self, transport: transports.DatagramTransport) -> None:
      pass

    def connection_lost(self, exc: Optional[Exception]) -> None:
      self.completed.set_result(True)

    def error_received(self, exc: Exception) -> None:
      self.completed.set_exception(exc)
    
    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
      tomr = datetime.now(tz=timezone.utc)        
      logger.debug(f"received UDP datagram from {addr[0]}:{addr[1]} at {tomr}")

      try:
        self.msg_queue.put_nowait((tomr, data))
      except asyncio.QueueFull:
        logger.critical(f"receive queue full - message from {addr[0]}:{addr[1]} dropped")


  def __init__(self, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)

    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    mreq = struct.pack('4sL', socket.inet_aton(settings.multicast_addr), socket.INADDR_ANY)
    self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    self.sock.bind(('', settings.multicast_port))
    
    self.completed = None

  async def start(self) -> None:
    loop = get_running_loop()
    self.completed = loop.create_future()    
    self.transport, self.protocol = await loop.create_datagram_endpoint(
      lambda: IpMulticast.Protocol(self.receive_queue, self.completed),
      sock=self.sock)
    try:
      await asyncio.create_task(self.run_transmitting())
    finally:
      self.transport.close()

  async def run_transmitting(self) -> None:
    while not self.completed.done():
      data = await self.transmit_queue.get()
      self.transport.sendto(data, (settings.multicast_addr, settings.multicast_port))
      self.transmit_queue.task_done()

