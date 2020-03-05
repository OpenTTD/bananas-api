# BaNaNaS API

[![GitHub License](https://img.shields.io/github/license/OpenTTD/bananas-api)](https://github.com/OpenTTD/bananas-api/blob/master/LICENSE)
[![GitHub Tag](https://img.shields.io/github/v/tag/OpenTTD/bananas-api?include_prereleases&label=stable)](https://github.com/OpenTTD/bananas-api/releases)
[![GitHub commits since latest release](https://img.shields.io/github/commits-since/OpenTTD/bananas-api/latest/master)](https://github.com/OpenTTD/bananas-api/commits/master)

[![GitHub Workflow Status (Testing)](https://img.shields.io/github/workflow/status/OpenTTD/bananas-api/Testing/master?label=master)](https://github.com/OpenTTD/bananas-api/actions?query=workflow%3ATesting)
[![GitHub Workflow Status (Publish Image)](https://img.shields.io/github/workflow/status/OpenTTD/bananas-api/Publish%20image?label=publish)](https://github.com/OpenTTD/bananas-api/actions?query=workflow%3A%22Publish+image%22)
[![GitHub Workflow Status (Deployments)](https://img.shields.io/github/workflow/status/OpenTTD/bananas-api/Deployment?label=deployment)](https://github.com/OpenTTD/bananas-api/actions?query=workflow%3A%22Deployment%22)

[![GitHub deployments (Staging)](https://img.shields.io/github/deployments/OpenTTD/bananas-api/staging?label=staging)](https://github.com/OpenTTD/bananas-api/deployments)
[![GitHub deployments (Production)](https://img.shields.io/github/deployments/OpenTTD/bananas-api/production?label=production)](https://github.com/OpenTTD/bananas-api/deployments)


This is the HTTP API for OpenTTD's content service, called BaNaNaS.
It works together with [bananas-server](https://github.com/OpenTTD/bananas-server), which serves the in-game client.

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
.env/bin/python -m bananas_api --web-port 8080 --tusd-port 1080 --storage local --index local --user developer
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
