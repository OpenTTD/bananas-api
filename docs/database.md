# Database

BaNaNaS stores its [database](https://github.com/OpenTTD/BaNaNaS) in a git repository on GitHub.
This is done to make it easier for any developer to do maintenance, as git is something developers are already known with when developing OpenTTD.
The database is stored in tha YAML format, and all components parse the full database on startup and keep it in memory.

# Layout

The top-level layout shows all the content-types supported.

In each folder are the unique-ids of content uploaded for that given type.
Unique-ids are presented in a human-readable format (which may include byte-swapping, depending on the content-type).
This makes, for example, finding back NewGRFs easier.

Inside the folder of a content, are various of files:

- `authors.yaml` - contains all the authors that have access to alter this content
- `global.yaml` - global information about the content.
Specific versions can overwrite most values; this works as a default for all versions.
- `versions/YYYYMMDDTHHMMSSZ.yaml` - a single uploaded version of the content

## authors.yaml

In the `authors` key there is a list, where each entry contains one of these keys:

- `display-name` (mandatory) - Name displayed everywhere
- `openttd` (optional) - Username as used with OpenTTD authentication mechanism (deprecated)
- `github` (optional) - GitHub user-id

Either `openttd` or `github` has to be given; both is possible, but not useful.

## global.yaml

There are several fields possible in this file, of which all can be overwritten by a specific version.
It is meant to make it easier for content-creators to only enter the name of their content once, for example, and have a single place to change it when ever they like.

The available fields are:

- `name`
- `description`
- `url`
- `tags`

## versions/YYYYMMDDTHHMMSSZ.yaml

Contains the exact information of this version of the content.
The fields from `global.yaml` can be omitted if they are unchanged.

The available fields are:

- `version`
- `license`
- `upload-date`
- `md5sum-partial` - See [md5sum](#md5sum) for more information
- `filesize`
- `availability` - See [availability](#availability) for more information.

And optionally all fields in `global.yaml`.

# Additional topics

## Availability

In a normal situation, BaNaNaS only shows the latest version of content to the user, to promote using the latest version.
These versions are marked as `new-games` for their `availability`.
That version should be used for a new game.

Older versions are made available for `savegames-only`, where you can only fetch the content if you have an existing savegame that uses it.
This allows, for example, multiplayer to work correctly, where the server doesn't have to use the latest version, yet clients can download the content when joining.

For some content the content-creator indicated he no longer wants it available for `new-games`.
In these cases, all versions are marked as `savegames-only`.

## md5sum

In the database a partial of the true md5sum is stored.
This prevents users without an existing savegame to download the `savegames-only` versions of content.
This is to comply with the Terms of Services BaNaNaS set out to its content-creators.

For more information, see [md5sum.md](md5sum.md).
