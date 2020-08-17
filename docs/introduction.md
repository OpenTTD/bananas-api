# Introduction

## What is BaNaNaS?

BaNaNaS is OpenTTD's content service.
It is the distribution platform OpenTTD uses to allow content-creators to offer additions to OpenTTD and users to use them in their games.

This services was created in 2007, and has been extended a few times over the years.
It currently offers the following capabilities:

- Uploading of new content by content-creators
- Editing / updating content by the original content-creator
- Downloading this content in-game by any user
- Browsing on the web what content is available

This can be done for the following content-type in OpenTTD:

- Base-Graphics
- Base-Sounds
- Base-Music
- NewGRFs
- AIs
- AI-Libraries
- Game-Scripts
- Game-Script-Libraries
- Scenarios
- Heightmaps

BaNaNaS is meant as an easy platform for both the content-creator as the end-user.

## Technical landscape

BaNaNaS is composed of several components:

- [BaNaNaS](https://github.com/OpenTTD/BaNaNaS) - Database of all the content available
- [bananas-server](https://github.com/OpenTTD/bananas-server) - Server with which the OpenTTD client communicates (custom TCP protocol)
- [bananas-api](https://github.com/OpenTTD/bananas-api) - The web-based API for various of frontends (published at [api.bananas.openttd.org](https://api.bananas.openttd.org))
- [bananas-frontend-cli](https://github.com/OpenTTD/bananas-frontend-cli) - The CLI frontend for the API
- [bananas-frontend-web](https://github.com/OpenTTD/bananas-frontend-web) - The web frontend for the API (published at [bananas.openttd.org](https://bananas.openttd.org))

There are two main methods these components connect to each other:

`BaNaNaS` -> `API` -> `Frontend Web` -> `Content-creators`

`BaNaNaS` -> `Server` -> `In-game client`

# More documentation

This folder documents BaNaNaS from a technical perspective.

- [api.md](api.md) - Explains what the API is about
- [database.md](database.md) - Explains how the database works
- [frontend.md](frontend.md) - Explains the frontends available
- [md5sum.md](md5sum.md) - Explains why in some parts you only see partials of md5sums
