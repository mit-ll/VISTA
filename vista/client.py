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

from enum import Enum
import urllib.parse
import json
import asyncio
import logging

from typing import Optional, Tuple, List
from uuid import UUID, uuid4
from pathlib import Path
from datetime import datetime, timedelta, timezone

import typer
import requests
from pydantic import parse_raw_as
from pydantic.json import pydantic_encoder

from .models.api import LoadSet, AuthorizationRequest, TokenKey, MessageKey
from .models.domain import Token
from . import transceiver

logging.basicConfig()

app = typer.Typer()
state = {}

@app.command(name="token_keys")
def get_token_keys(nbf: datetime = None, exp: datetime = None) -> List[TokenKey]:

    parsed_url = urllib.parse.urlparse(state["url"])
    parsed_url = parsed_url._replace(path= f"token_keys")
    
    r = requests.get(urllib.parse.urlunparse(parsed_url), {'nbf': nbf, 'exp': exp})
    r.raise_for_status()
    token_keys = parse_raw_as(List[TokenKey], r.text)

    if state['out'] is None:
        typer.echo(json.dumps(token_keys, indent=2, default=pydantic_encoder))
    else:
        state['out'].write_text(json.dumps(token_keys, indent=2, default=pydantic_encoder))

    return token_keys

@app.command(name="message_keys")
def get_message_keys(nbf: datetime = None, exp: datetime = None) -> List[MessageKey]:

    parsed_url = urllib.parse.urlparse(state["url"])
    parsed_url = parsed_url._replace(path= f"message_keys")
    
    r = requests.get(urllib.parse.urlunparse(parsed_url), {'nbf': nbf, 'exp': exp})
    r.raise_for_status()
    message_keys = parse_raw_as(List[MessageKey], r.text)

    if state['out'] is None:
        typer.echo(json.dumps(message_keys, indent=2, default=pydantic_encoder))
    else:
        state['out'].write_text(json.dumps(message_keys, indent=2, default=pydantic_encoder))

    return message_keys

@app.command(name="loadset")
def get_loadset(gufi: UUID) -> LoadSet:
    
    parsed_url = urllib.parse.urlparse(state["url"])
    parsed_url = parsed_url._replace(path= f"loadset/{gufi}")
    
    r = requests.get(urllib.parse.urlunparse(parsed_url))
    r.raise_for_status()
    load_set = LoadSet.parse_raw(r.text)

    if state['out'] is None:
        typer.echo(load_set.json())
    else:
        state['out'].write_text(load_set.json(indent=2))

    return load_set

@app.command(name="authorize")
def request_authorization(gufi: Optional[UUID] = None, start: Optional[datetime] = None, end: Optional[datetime] = None, duration: Optional[float] = None, bbox: Optional[Tuple[float, float, float, float]] = typer.Option((None, None, None, None))) -> LoadSet:
    if gufi is None:
        gufi = uuid4()

    if None in bbox:
        bbox = (-71.79,41.945,-70.57,42.725)

    if start is None:
        if duration is None:
            typer.echo('One of "start" or "duration" is required')
            raise typer.Abort() 
        start = datetime.now(tz = timezone.utc)

    if None not in (duration, end):
        typer.echo('Cannot specify both "end" and "duration"')
        raise typer.Abort() 

    if end is None:
        if duration is None:
            typer.echo('Must specify either "end" and "duration"')
            raise typer.Abort() 
        end = start + timedelta(minutes=duration)

    parsed_url = urllib.parse.urlparse(state["url"])
    parsed_url = parsed_url._replace(path= "authorization")

    request = AuthorizationRequest(
        gufi = gufi,
        nbf = start,
        exp = end,
        bbox = bbox
    )
    
    r = requests.post(urllib.parse.urlunparse(parsed_url), json=json.loads(request.json()))
    r.raise_for_status()
    load_set = LoadSet.parse_raw(r.text)

    if state['out'] is None:
        typer.echo(load_set.json())
    else:
        state['out'].write_text(load_set.json(indent=2))

    return load_set

class Config(str, Enum):
    baseline = "baseline"
    blackhat = "blackhat"

@app.command(name="run")
def run(gufi: Optional[UUID] = None, loadset: Optional[Path] = typer.Option(None, exists=True, dir_okay = False, readable=True), duration: Optional[float] = None, bbox: Optional[Tuple[float, float, float, float]] = typer.Option((None, None, None, None)), config:Config = Config.baseline):

    if config == Config.blackhat:
        token_keys = get_token_keys()
        message_keys = get_message_keys()
        load_set = LoadSet.construct(token_keys = token_keys, message_keys = message_keys)

        link_type = transceiver.link.IpMulticast
        application_type = transceiver.application.BlackHat

        asyncio.run(transceiver.start(link_type, application_type, load_set = load_set))

    elif config == Config.baseline:
        if loadset is None:
            if gufi is None:
                if duration is None:
                    typer.echo('Must specify gufi, loadset, or duration')
                    raise typer.Abort() 
                load_set = request_authorization(duration = duration, bbox = bbox)
            else:    
                load_set = get_loadset(gufi)
        else:
            load_set = LoadSet.parse_file(loadset)

        bbox =  Token.unpack(load_set.tokens[0].value).payload.bbox

        link_type = transceiver.link.IpMulticast
        nav_src = transceiver.nav_src.Random(bbox)
        application_type = transceiver.application.Baseline    

        asyncio.run(transceiver.start(link_type, application_type, nav_src, load_set))

@app.callback()
def main(url: str = 'http://localhost:8000', out: Optional[Path] = typer.Option(None, exists=False, dir_okay = False, writable=True), verbose: bool = False):
    state["url"] = url
    state["out"] = out

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

if __name__ == "__main__":
    app()