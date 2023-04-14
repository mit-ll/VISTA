# VISTA

VISTA is a proof of concept for a V2V Security, Identity, and Trust Architecture (VISTA) example security framework implemented in Python.  This proof of concept is not an implied endorsement that the VISTA framework is either sufficient or unique as a V2V security solution, but instead exists as a research and development baseline for community experimentation.  Furthermore, this proof of concept implementation, while substantially functional, is not of production quality.  Features and best-practices must be assumed to remain incomplete and their absence is not an endorsement of their necessitity or otherwise.

Major components include an **authority** responsible for authorizing link participants and managing cryptographic keys together with an associated REST API **server**, a **transceiver** which produces periodic squitters and validates received link messages, and a  **client** CLI tool allowing user interaction with the authority server and management of transceivers.  The **crypto** package implements utility functions and wrappers around the cryptographic libraries, while the **models** package includes data models for the REST API, domain (V2V link), and SQL backend.

## Installation

Vista requires Python 3.7.  Instructions for installing the Stanford PBC and Charm-crypto libraries are available [here](https://github.com/JHUISI/charm#readme)

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install the remaining requirements

```bash
pip install -r requirements.txt
```

## Usage

From the root of the repo, run the authority server listening for local-only connections:

```bash
python -m uvicorn vista.server:app
```

Run the client to request a 10 minute authorization from the authority and start a transceiver

```bash
python -m vista.client run --duration 10
```

Client options can be viewed from the CLI help menu

```bash
python -m vista.client [authorize|loadset|run] --help
```

Authority and server parameters can be set in environment variables or a `vista.env` file

An entire ecosystem, including the authority server and multiple clients can be instantiated and run using Docker-compose

```bash
docker-compose up --scale client=10
```

## Distribution

DISTRIBUTION STATEMENT A. Approved for public release. Distribution is unlimited.

This material is based upon work supported by the Federal Aviation Administration under Air Force Contract No. FA8702-15-D-0001. Any opinions, findings, conclusions or recommendations expressed in this material are those of the author(s) and do not necessarily reflect the views of the Federal Aviation Administration.

© 2023 Massachusetts Institute of Technology.

Subject to FAR52.227-11 Patent Rights - Ownership by the contractor (May 2014)

The software/firmware is provided to you on an As-Is basis

Delivered to the U.S. Government with Unlimited Rights, as defined in DFARS Part 252.227-7013 or 7014 (Feb 2014). Notwithstanding any copyright notice, U.S. Government rights in this work are defined by DFARS 252.227-7013 or DFARS 252.227-7014 as detailed above. Use of this work other than as specifically authorized by the U.S. Government may violate any copyrights that exist in this work.