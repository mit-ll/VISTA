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

from pydantic import BaseSettings

class Settings(BaseSettings):
    db_url: str = "sqlite:///./vista.db"
    time_resolution_ms: float = 500
    min_datetime: str = '2020-01-01T00:00:00+00:00'
    multicast_port: int = 1935
    multicast_addr: str = '224.0.0.250'
    key_rotation_mins: float = 5
    key_expiration_buffer_ms: float = 500
    num_threads: int = 5
    broadcast_period_secs: float = 1

    class Config:
        env_prefix = "vista"
        env_file = 'vista.env'
        env_file_encoding = 'utf-8'

settings = Settings()