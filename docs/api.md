# API

Except for the server serving the in-game clients, all communication about BaNaNaS goes via the API.
The API allows both reading from the database as writing to it, given you have permissions to do so.

## Authentication

Authentication is done via GitHub OAuth flow.
There is no scope requested, as the only information requires is the ID GitHub assigned to the user.
Based on the `authors.yaml` from the database, permission is granted to the content the user is owner of.

## New uploads

Any signed-in user can upload new content (content of which we haven't seen the unique-id yet).
Every upload is validated to check if it is valid content.
For example, for NewGRFs it checks if it is really a NewGRF that is being uploaded, etc.
It also validates that only one content-type is uploaded at the time, and that the administration around it is correct.
The exact rules can be found in the code.

## Updating existing content

Content a user is owner of can be modified freely by that user.
All fields can be modified, and new versions can be uploaded.
A user cannot delete existing content, as that might break existing games running.
In case this is really needed, a user can contact a developer to take action.
