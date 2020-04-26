import asyncio
import click
import secrets

from .click import (
    click_additional_options,
    import_module,
)
from ..new_upload.session import invalidate_session_of_user

_sessions_by_bearer = {}
_sessions_by_code = {}

_methods = {}

TIME_BETWEEN_CHECKS = None
SESSION_EXPIRE = None
LOGIN_EXPIRE = None


def create_user_with_method(method, redirect_uri, code_challenge):
    user = _methods[method](redirect_uri, code_challenge)
    _sessions_by_code[user.code] = user
    return user


def create_bearer_token():
    # Change on collision is really low, but would be really annoying. So
    # simply protect against it by looking for an unused UUID.
    bearer_token = secrets.token_hex(16)
    while bearer_token in _sessions_by_bearer:
        bearer_token = secrets.token_hex(16)

    return bearer_token


def get_user_by_bearer(bearer_token):
    user = _sessions_by_bearer.get(bearer_token)
    if not user:
        return None

    return user.check_expire()


def get_user_by_code(code):
    user = _sessions_by_code.get(code)
    if not user:
        return None

    return user.check_expire()


def handover_to_bearer(user, bearer_token):
    _sessions_by_bearer[bearer_token] = user
    del _sessions_by_code[user.code]


def delete_user(user):
    invalidate_session_of_user(user)

    if user.bearer_token:
        del _sessions_by_bearer[user.bearer_token]
    if user.code:
        del _sessions_by_code[user.code]


def get_user_methods():
    return _methods.keys()


def get_user_method(method):
    return _methods.get(method)


def register_webroutes(webapp):
    for method in _methods.values():
        if hasattr(method, "routes"):
            webapp.add_routes(method.routes)


async def check_expire():
    while True:
        await asyncio.sleep(TIME_BETWEEN_CHECKS)

        # Cast it into a list, as on expire we are going to modify _session.
        # This would cause "dictionary changed size during iteration"
        # otherwise.
        for user in list(_sessions_by_bearer.values()):
            user.check_expire()
        for user in list(_sessions_by_code.values()):
            user.check_expire()


def get_session_expire():
    return SESSION_EXPIRE


def get_login_expire():
    return LOGIN_EXPIRE


@click_additional_options
@click.option(
    "--user",
    help="User backend to use (can have multiple).",
    type=click.Choice(["developer", "github", "openttd"], case_sensitive=False),
    required=True,
    multiple=True,
    callback=import_module("bananas_api.user", "User"),
)
@click.option(
    "--user-session-expire",
    help="Time for a session to expire (measured from the moment of login).",
    default=60 * 60 * 14,
    show_default=True,
    metavar="SECONDS",
)
@click.option(
    "--user-login-expire",
    help="Time for a login attempt to expire.",
    default=60 * 10,
    show_default=True,
    metavar="SECONDS",
)
@click.option(
    "--user-session-expire-schedule",
    help="The interval between check if a user session is expired.",
    default=60 * 15,
    show_default=True,
    metavar="SECONDS",
)
def click_user_session(user, user_session_expire, user_login_expire, user_session_expire_schedule):
    global SESSION_EXPIRE, LOGIN_EXPIRE, TIME_BETWEEN_CHECKS

    SESSION_EXPIRE = user_session_expire
    LOGIN_EXPIRE = user_login_expire
    TIME_BETWEEN_CHECKS = user_session_expire_schedule

    for user_class in user:
        _methods[user_class.method] = user_class

    # Start the expire check via an async task
    loop = asyncio.get_event_loop()
    loop.create_task(check_expire())
