import asyncio
import click
import secrets

from .click import (
    click_additional_options,
    import_module,
)

_sessions = {}
_methods = {}

TIME_BETWEEN_CHECKS = None
SESSION_EXPIRE = None


def create_user_with_method(method, redirect_uri=None):
    # Change on collision is really low, but would be really annoying. So
    # simply protect against it by looking for an unused UUID.
    bearer_token = secrets.token_hex(16)
    while bearer_token in _sessions:
        bearer_token = secrets.token_hex(16)

    user = _methods[method](bearer_token, redirect_uri)

    _sessions[bearer_token] = user
    return user, bearer_token


def get_user_by_bearer(bearer_token):
    user = _sessions.get(bearer_token)
    if not user:
        return None

    return user.check_expire()


def delete_user(user):
    del _sessions[user.bearer_token]


def get_user_methods():
    return _methods.keys()


def register_webroutes(webapp):
    for method in _methods.values():
        if hasattr(method, "routes"):
            webapp.add_routes(method.routes)


async def check_expire():
    while True:
        await asyncio.sleep(TIME_BETWEEN_CHECKS)

        for user in _sessions.values():
            user.check_expire()


def get_session_expire():
    return SESSION_EXPIRE


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
    "--user-session-expire-schedule",
    help="The interval between check if a user session is expired.",
    default=60 * 15,
    show_default=True,
    metavar="SECONDS",
)
def click_user_session(user, user_session_expire, user_session_expire_schedule):
    global SESSION_EXPIRE, TIME_BETWEEN_CHECKS

    SESSION_EXPIRE = user_session_expire
    TIME_BETWEEN_CHECKS = user_session_expire_schedule

    for user_class in user:
        _methods[user_class.method] = user_class

    # Start the expire check via an async task
    loop = asyncio.get_event_loop()
    loop.create_task(check_expire())
