import dateutil.parser
import json

from aiohttp import web

from .enums import ContentType
from .user_session import (
    get_user_by_bearer,
    get_user_methods,
)


class JSONException(web.HTTPException):
    def __init__(
        self, data, *, status=400, reason=None, headers=None, content_type="application/json", dumps=json.dumps
    ):
        self.status_code = status
        text = dumps(data)
        super().__init__(text=text, reason=reason, headers=headers, content_type=content_type)


def in_path_content_type(content_type):
    try:
        content_type = ContentType(content_type)
    except Exception:
        raise JSONException({"message": "content_type is invalid"})

    return content_type


def in_path_unique_id(unique_id):
    if len(unique_id) != 8 or any([u not in ("abcdef1234567890") for u in unique_id]):
        raise JSONException({"message": "unique_id is invalid"})

    return unique_id


def in_path_upload_date(upload_date):
    try:
        upload_date = dateutil.parser.isoparse(upload_date)
    except Exception:
        raise JSONException({"message": "upload_date is not a valid ISO 8601 date"})

    if not upload_date.tzinfo:
        raise JSONException({"message": "upload_date is missing a timezone"})

    return upload_date


def in_path_file_uuid(file_uuid):
    # tusd generates these uuids, and the least we know is that they are
    # at least four characters long.
    if len(file_uuid) < 4:
        raise JSONException({"message": "file_uuid seems to be an invalid uuid"})

    return file_uuid


def in_path_upload_token(upload_token):
    # We generated this token with token_hex(16), and as such should always
    # be 32 in length.
    if len(upload_token) != 32:
        raise JSONException({"message": "upload_token is not a valid uuid"})

    return upload_token


def in_header_authorization_pre(headers):
    authorization = headers.get("Authorization")
    if not authorization:
        raise JSONException({"message": "no authentication header"}, status=401)

    bearer_word, _, bearer_token = authorization.partition(" ")

    if bearer_word != "Bearer":
        raise JSONException({"message": "invalid authentication header"}, status=401)

    if len(bearer_token) != 32:
        raise JSONException({"message": "invalid authentication header; bearer is not a valid uuid"})

    user = get_user_by_bearer(bearer_token)

    if user is None:
        raise JSONException({"message": "invalid authentication token"}, status=401)

    return user


def in_header_authorization(headers):
    user = in_header_authorization_pre(headers)

    if not user.is_logged_in():
        raise JSONException({"message": "invalid authentication token"}, status=401)

    return user


def in_query_since(since):
    if since is None:
        return None

    try:
        since = dateutil.parser.isoparse(since)
    except Exception:
        raise JSONException({"message": "since is not a valid ISO 8601 date"})

    if not since.tzinfo:
        raise JSONException({"message": "since is missing a timezone"})

    return since


def in_query_authorize_audience(audience):
    if audience is None:
        raise JSONException({"message": "audience is not set in query-string"})

    if audience not in get_user_methods():
        raise JSONException({"message": f"audience is not one of the following: {get_user_methods()}"})

    return audience


def in_query_authorize_response_type(response_type):
    if response_type != "code":
        raise JSONException({"message": "response_type should be 'code'"})

    return response_type


def _redirect_uri(redirect_uri):
    # Localhost is needed for CLI access; and serving that via https is not
    # something that is a solved problem.
    if not redirect_uri.startswith("https://") and not redirect_uri.startswith("http://localhost:"):
        raise JSONException({"message": "redirect_uri should always start with https://"})

    return redirect_uri


def in_query_authorize_redirect_uri(redirect_uri):
    if redirect_uri is None:
        raise JSONException({"message": "redirect_uri is not set in query-string"})

    return _redirect_uri(redirect_uri)


def in_query_authorize_code_challenge_method(code_challenge_method):
    if code_challenge_method != "S256":
        raise JSONException({"message": "code_challenge_method should be 'S256'"})

    return code_challenge_method


def in_query_github_code(code):
    if code is None:
        raise JSONException({"message": "code is not set in query-string"})

    # This code is sent by GitHub, and should be at least 20 characters.
    # GitHub makes no promises over the length.
    if len(code) < 20:
        raise JSONException({"message": "code seems to be an invalid GitHub callback code"})

    return code


def in_query_github_state(state):
    if state is None:
        raise JSONException({"message": "state is not set in query-string"})

    # We generated this state with token_hex(16), and as such should always
    # be 32 in length.
    if len(state) != 32:
        raise JSONException({"message": "state is not a valid uuid"})

    return state


def in_post_token_code(code):
    if code is None:
        raise JSONException({"message": "code is not set in payload"})

    # We generated this code with token_hex(16), and as such should always
    # be 32 in length.
    if len(code) != 32:
        raise JSONException({"message": "code is an invalid code"})

    return code


def in_post_token_grant_type(grant_type):
    if grant_type != "authorization_code":
        raise JSONException({"message": "grant_type should be 'authorization_code'"})

    return grant_type


def in_post_token_redirect_uri(redirect_uri):
    if redirect_uri is None:
        raise JSONException({"message": "redirect_uri is not set in POST JSON body"})

    return _redirect_uri(redirect_uri)
