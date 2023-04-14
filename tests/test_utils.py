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

from pytest import raises

from vista.utils import bbox_includes, encode_datetime_as_int, ROUND_CEILING, ROUND_FLOOR
from vista.settings import settings
def test_bbox_includes():

    # nominal bbox includes interior and boundary points
    bbox = (-40,30,-30,40)
    points = [
        (-35,35),
        (-40, 30),
        (-40, 40),
        (-30, 40),
        (-30, 30)]
    for point in points:
        assert bbox_includes(bbox, point) is True

    # nominal bbox doesn't incude exterior points along all faces
    points = [
        (-45, 35),
        (-25, 35),
        (-35, 45),
        (-35, 25)]
    for point in points:
        assert bbox_includes(bbox, point) is False

    # bbox overlapping antimeridian includes interior points along antimeridian
    bbox = (170, -10, -170, 10)
    points = [
        (-180,0),
        (180, 0)]
    for point in points:
        assert bbox_includes(bbox, point) is True

    # bbox overlapping antimeridian doesn't include exterior points, including along prime meridian 
    points = [
        (0,0),
        (165, 0),
        (-165, 0)]
    for point in points:
        assert bbox_includes(bbox, point) is False

    #Latitude bounds checking
    bboxes = [(30, -91,-30,40),
              (-40,30,40, 91)]
    point = (0,0)

    for bbox in bboxes:
        with raises(ValueError) as excinfo:
            bbox_includes(bbox, point)
        assert "Latitude out of range" in str(excinfo.value)

    bbox = (-40,30,-30,40)
    points = [(0, -91),
            (0, 91)]

    for point in points:
        with raises(ValueError) as excinfo:
            bbox_includes(bbox, point)
        assert "Latitude out of range" in str(excinfo.value)

    #Longitude bounds checking
    bboxes = [(181,-40,-30,40),
              (-40,30,-181,-30)]
    point = (0,0)

    for bbox in bboxes:
        with raises(ValueError) as excinfo:
            bbox_includes(bbox, point)
        assert "Longitude out of range" in str(excinfo.value)

    bbox = (-40,30,-30,40)
    points = [(181, 0),
            (-181, 0)]

    for point in points:
        with raises(ValueError) as excinfo:
            bbox_includes(bbox, point)
        assert "Longitude out of range" in str(excinfo.value)        


def test_encode_datetime_as_int():

    min_datetime = datetime.fromisoformat(settings.min_datetime)
    time_resolution = timedelta(milliseconds=settings.time_resolution_ms)

    assert encode_datetime_as_int(min_datetime, ROUND_FLOOR) == 0
    assert encode_datetime_as_int(min_datetime, ROUND_CEILING) == 0
    assert encode_datetime_as_int(min_datetime + 0.9 * time_resolution, ROUND_FLOOR) == 0
    assert encode_datetime_as_int(min_datetime + 0.9 * time_resolution, ROUND_CEILING) == 1
    assert encode_datetime_as_int(min_datetime + time_resolution, ROUND_FLOOR) == 1
    assert encode_datetime_as_int(min_datetime + time_resolution, ROUND_CEILING) == 1
    assert encode_datetime_as_int(min_datetime + 1.1 * time_resolution, ROUND_FLOOR) == 1
    assert encode_datetime_as_int(min_datetime + 1.1 * time_resolution, ROUND_CEILING) == 2



