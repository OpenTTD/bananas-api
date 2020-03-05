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
    if len(file_uuid) < 4:
        raise JSONException({"message": "file_uuid seems to be an invalid uuid"})

    return file_uuid


def in_path_upload_token(upload_token):
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


def in_query_login_method(method):
    if method is None:
        raise JSONException({"message": "method is not set in query-string"})

    if method not in get_user_methods():
        raise JSONException({"message": f"method is not one of the following: {get_user_methods()}"})

    return method


def in_query_github_code(code):
    if code is None:
        raise JSONException({"message": "code is not set in query-string"})

    if len(code) < 20:
        raise JSONException({"message": "code seems to be an invalid GitHub callback code"})

    return code


def in_query_github_state(state):
    if state is None:
        raise JSONException({"message": "state is not set in query-string"})

    if len(state) != 32:
        raise JSONException({"message": "state is not a valid uuid"})

    return state


def in_query_login_redirect_uri(redirect_uri):
    if redirect_uri is None:
        return None

    # Localhost is needed for CLI access; and serving that via https is not
    # something that is a solved problem.
    if not redirect_uri.startswith("https://") and not redirect_uri.startswith("http://localhost:"):
        raise JSONException({"message": "redirect_uri should always start with https://"})

    return redirect_uri
