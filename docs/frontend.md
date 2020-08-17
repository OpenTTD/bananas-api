# Frontend

BaNaNaS has several frontends for its service.
Most frontends use the API to communicate with, with the exception of the server serving the in-game client.

- [bananas-server](https://github.com/OpenTTD/bananas-server) - Server with which the OpenTTD client communicates (custom TCP protocol)
- [bananas-frontend-cli](https://github.com/OpenTTD/bananas-frontend-cli) - The CLI frontend for the API
- [bananas-frontend-web](https://github.com/OpenTTD/bananas-frontend-web) - The web frontend for the API (published at [bananas.openttd.org](https://bananas.openttd.org))

## BaNaNaS server

This server serves the files to the in-game client.
It does not use the API, but reads the [BaNaNaS database](database.md) directly.
This is mostly done for performance reasons, as there are thousands of requests a day to this server, of which most are in bulk.

Files requested for download are redirects to HTTP to download the files from our CDN, if possible.
As older clients do not support this, and HTTP might be blocked from access, the in-game client can fallback to the custom TCP protocol to receive the file.

## BaNaNaS Frontend CLI

Mostly meant for advanced users and those who want to automate the uploading of their content, for example via a GitHub Action on tagging.
The CLI allows uploading new content via the API to BaNaNaS, after authentication.

## BaNaNas Frontend web

Serves two purposes:

1) it allows content-creators to upload new content
2) it allows anonymous users to view current content

They are both a wrapper around the API, to make access easier.
For the first it also helps the content-creator by introducing a workflow to get your content uploaded.

They are both aimed to be self-explaining and require as little user-documentation as possible.
In general, it should not be possible to do things wrong; otherwise it is considered a bug.
