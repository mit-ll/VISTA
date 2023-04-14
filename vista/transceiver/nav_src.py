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

from datetime import datetime
from abc import ABC, abstractmethod
from typing import Tuple

from ..models.domain import StateUpdate

class NavSource(ABC):

  @abstractmethod
  def get_state(self, toa: datetime) -> StateUpdate:
    pass

class Random(NavSource):

  def __init__(self, bbox:Tuple[float, float, float, float] = None) -> None:
      if bbox is None:
        bbox = (-180, -90, 180, 90)
      self.bbox = bbox
      

  def get_state(self, toa: datetime) -> StateUpdate:
      return StateUpdate.parse_obj(
        {
        'lat_deg'     : random.uniform(self.bbox[1], self.bbox[3]),
        'lon_deg'     : random.uniform(self.bbox[0], self.bbox[2]),
        'alt_hae_ft'  : random.uniform(0, 10000),
        'vel_ew_fps'  : random.uniform(-250,250),
        'vel_ns_fps'  : random.uniform(-250,250),
        'vel_vert_fps': random.uniform(-50,50),
        'toa_utc'     : toa.timestamp()
        })