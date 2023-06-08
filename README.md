# BaNaNaS API

[![GitHub License](https://img.shields.io/github/license/OpenTTD/bananas-api)](https://github.com/OpenTTD/bananas-api/blob/main/LICENSE)

This is the HTTP API for OpenTTD's content service, called BaNaNaS.
It works together with [bananas-server](https://github.com/OpenTTD/bananas-server), which serves the in-game client.

See [introduction.md](docs/introduction.md) for more documentation about the different BaNaNaS components and how they work together.

The API is documented on [SwaggerHub](https://app.swaggerhub.com/apis-docs/OpenTTD/OpenTTD-content-api/1.0.0).

## Development

This API is written in Python 3.8 with aiohttp, and makes strong use of asyncio.

### Running a local server

#### Dependencies

- Python3.8 or higher.
- [tusd](https://github.com/tus/tusd). For example, copy the `tusd` binary in your `~/.local/bin`.

#### Preparing your venv

To start it, you are advised to first create a virtualenv:

```bash
python3 -m venv .env
.env/bin/pip install -r requirements.txt
```

#### Starting a local server

You can start the HTTP server by running:

```bash
.env/bin/python -m bananas_api --web-port 8080 --tusd-port 1080 --storage local --index local --user developer --client-file clients-development.yaml
```

This will start the API on port 8080 for you to work with locally.

### Running via docker

```bash
docker build -t openttd/bananas-api:local .
export BANANAS_COMMON=$(pwd)/../bananas-common
mkdir -p "${BANANAS_COMMON}/local_storage" "${BANANAS_COMMON}/BaNaNaS"
docker run --rm -p 127.0.0.1:8080:80 -p 127.0.0.1:1080:1080 -v "${BANANAS_COMMON}/local_storage:/code/local_storage" -v "${BANANAS_COMMON}/BaNaNaS:/code/BaNaNaS" openttd/bananas-api:local
```

The mount assumes that [bananas-server](https://github.com/OpenTTD/bananas-server) and this repository has the same parent folder on your disk, as both servers need to read the same local storage.

### Files upload (tusd)

tusd runs on its own port (1080 by default), and listens on `/new-package/files`.
With other words: the webserver does not forward that URL to tusd.
This means that for clients, you need to contact two endpoints:

- the web-port for everything except `/new-package/files`.
- the tusd-port for `/new-package/files`.

In production the Load Balancer redirects the URLs to the right ports, but during development this is something to keep in mind.

[bananas-frontend-cli](https://github.com/OpenTTD/bananas-frontend-cli) for example allows you to define the web-endpoint and the tusd-endpoint.

## Regions

To unify the way authors indicate what region their content is about, we have a built-in list of supported regions.
This is a combination of the [UN M49](https://unstats.un.org/unsd/methodology/m49/overview) list and ISO 3166-1 / 3166-2 list.

- The 3166-1 / 3166-2 list is easiest found in the Debian `iso-codes` package, after which it is located in `/usr/share/iso-codes/json/iso_3166-[12].json`.
- The UN M49 can be found [here](https://unstats.un.org/unsd/methodology/m49/overview).
