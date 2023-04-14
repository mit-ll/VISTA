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
import logging

logger = logging.getLogger(__name__)

from typing import Optional, Type
from asyncio import Queue

from ..models.api import LoadSet

from .nav_src import NavSource, Random as RandomNavSource
from .application import Application
from .link import Link


async def start(link_type: Type[Link], application_type: Type[Application], nav_src: Optional[NavSource] = None, load_set: Optional[LoadSet] = None) -> None:
  receive_queue = Queue()
  transmit_queue = Queue()
  application = application_type(receive_queue, transmit_queue, load_set, nav_src)
  link = link_type(receive_queue, transmit_queue)
  await asyncio.gather(link.start(), application.start())