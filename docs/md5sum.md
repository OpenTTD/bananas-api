# md5sum

## Introduction

Before we explain what this is all about `md5sum` and `md5sum-partial`, we first need to set the stage.

One of the things BaNaNaS sets out in its [Terms of Service](https://bananas.openttd.org/manager/tos), that only the latest version of content is available for download (point 3).
Older versions are only available for loading savegames, if they contain the older version (point 4).

Downloads are available via our CDN, which is public but doesn't allow listing.

`md5sum` is the checksum of the upload as done by the content-creator.
Important to note, depending on the content-type, it doesn't have to be a checksum of the full file; it can be only of parts of files.
For example, NewGRFs don't include the sprites themselves in the checksum.

Savegames store the `md5sum` of content in use during the game.

## Keeping a secret

BaNaNaS implements the above constraints by keeping a few secrets.
Nowhere BaNaNaS publishes in public the `md5sum` in full.
Because of this, it becomes non-trivial to download older versions of content if you do not already know the `md5sum`, keeping our promise of point 4.

## Partials

As the server and API still needs to know what version of the content is referred to, in the database is stored a partial of the `md5sum`, called `md5sum-partial`.
This partial is the last 32 bits of the checksum, meaning 96 bits are still hidden from view.

During uploading of new content, a few things are validated:

1) There is no other content with the exact same `md5sum`
2) There is no other version of your content with the exact same `md5sum-partial`

The first one (mostly) indicates that another user uploaded the exact same content as someone else.
This is not allowed by BaNaNaS, as only the original author is allowed to upload content.
For our "secret" this is ideal, as it means we don't have to worry about duplicated `md5sum`s.

The second can strictly seen be an issue, where by a very very very very small chance you made changes which resulted in a different `md5sum` but in an identical `md5sum-partial`.
The chances on this are very low, and if you happen to hit this case: please buy a lottery ticket.
Nevertheless, the user can easily resolve this problem by making any change to their content and uploading it again.

## End-result

With all this in place, we can now comply to our Terms of Service.
Although strictly seen someone can scan for the full `md5sum`, it has to iterate over 2^96 combinations (worst case).
This is most likely caught by the rate-limiter in place, further reducing the likelihood someone downloading a non-latest version of a content, without having a savegame that already used it.
