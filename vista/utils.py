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

from datetime import datetime, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR
from typing import Tuple

from .settings import settings

TIME_RESOLUTION = timedelta(milliseconds=settings.time_resolution_ms)
MIN_DATETIME = datetime.fromisoformat(settings.min_datetime)

def encode_datetime_as_int(val: datetime, rounding=ROUND_FLOOR) -> int:
    if val < MIN_DATETIME:
        raise ValueError(f"datetimes must be no earlier than {MIN_DATETIME}")

    if rounding is ROUND_FLOOR:
        val = val - (val - MIN_DATETIME) % TIME_RESOLUTION
    elif rounding is ROUND_CEILING:
        val = val + (MIN_DATETIME - val) % TIME_RESOLUTION
    else:
        raise ValueError("rounding must be one of ROUND_CEILING or ROUND_FLOOR")

    return int((val - MIN_DATETIME) / TIME_RESOLUTION)

def decode_datetime_from_int(val: int) -> datetime:
    return val*TIME_RESOLUTION+MIN_DATETIME

def bbox_includes(bbox: Tuple[float, float, float, float], point: Tuple[float, float]) -> bool:
    # from RFC7946:
    #    point: longitude and latitude, or easting and northing, precisely in that order
    #    bbox: southwesterly point followed by northeasterly point

    for lon, lat in (point, bbox[:2], bbox[2:]):
        if abs(lon) > 180:
            raise ValueError("Longitude out of range")
        if abs(lat) > 90:
            raise ValueError("Latitude out of range")

    lon, lat = point
    west_bound, south_bound = bbox[:2]
    east_bound, north_bound = bbox[2:]

    if lat > north_bound or lat < south_bound:
        return False

    # if east_bound < west_bound, bbox includes antimeridian
    if east_bound < west_bound:
        return lon >= west_bound or lon <= east_bound
    else:
        return lon >= west_bound and lon <= east_bound 
        
    