import asyncio
import click
import secrets

from aiohttp import web
from aioauth_client import GithubClient

from .base import User as BaseUser
from ..helpers.click import click_additional_options
from ..helpers.web_routes import (
    in_query_github_code,
    in_query_github_state,
)

GITHUB_CLIENT_ID = None
GITHUB_CLIENT_SECRET = None
GITHUB_LOGIN_TIMEOUT = None

_github_states = {}


@click_additional_options
@click.option("--user-github-client-id", help="GitHub client ID. (user=github only)")
@click.option(
    "--user-github-client-secret",
    help="GitHub client secret. Always use this via an environment variable! (user=github only)",
)
@click.option(
    "--user-github-login-timeout",
    help="Time a user has to login via GitHub OAuth. (user=github only)",
    default=60 * 15,
    show_default=True,
    metavar="SECONDS",
)
def click_user_github(user_github_client_id, user_github_client_secret, user_github_login_timeout):
    global GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_LOGIN_TIMEOUT

    GITHUB_CLIENT_ID = user_github_client_id
    GITHUB_CLIENT_SECRET = user_github_client_secret
    GITHUB_LOGIN_TIMEOUT = user_github_login_timeout


class User(BaseUser):
    method = "github"
    routes = web.RouteTableDef()

    def __init__(self, bearer_token, redirect_uri=None):
        super().__init__(bearer_token, redirect_uri)

        if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
            raise Exception("GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET should be set via environment")

        self._github = GithubClient(client_id=GITHUB_CLIENT_ID, client_secret=GITHUB_CLIENT_SECRET)

    def get_authorize_url(self):
        # Change on collision is really low, but would be really annoying. So
        # simply protect against it by looking for an unused UUID.
        state = secrets.token_hex(16)
        while state in _github_states:
            state = secrets.token_hex(16)
        self._state = state

        _github_states[self._state] = self

        loop = asyncio.get_event_loop()
        self._timer = loop.create_task(self._timeout_github())

        # We don't set any scope, as we only want the username + id
        return self._github.get_authorize_url(state=self._state)

    async def _timeout_github(self):
        await asyncio.sleep(GITHUB_LOGIN_TIMEOUT)

        self._timer = None
        self._forget_github_state()

    @staticmethod
    def get_by_state(state):
        if state not in _github_states:
            return None

        user = _github_states[state]
        user._forget_github_state()

        return user

    def logout(self):
        self._forget_github_state()

        super().logout()

    async def validate_code(self, code):
        # Validate the code and fetch the user info
        await self._github.get_access_token(code)
        user, _ = await self._github.user_info()

        self.display_name = user.username
        self.id = str(user.id)

    def _forget_github_state(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None

        if self._state:
            del _github_states[self._state]

        self._state = None

    @staticmethod
    @routes.get("/user/github-callback")
    async def login_github_callback(request):
        code = in_query_github_code(request.query.get("code"))
        state = in_query_github_state(request.query.get("state"))

        user = User.get_by_state(state)
        if user is None:
            return web.HTTPNotFound()

        await user.validate_code(code)
        if user.redirect_uri:
            return web.HTTPFound(location=user.redirect_uri)
        return web.HTTPNoContent()
