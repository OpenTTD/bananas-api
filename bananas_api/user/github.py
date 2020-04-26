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

_github_states = {}


@click_additional_options
@click.option("--user-github-client-id", help="GitHub client ID. (user=github only)")
@click.option(
    "--user-github-client-secret",
    help="GitHub client secret. Always use this via an environment variable! (user=github only)",
)
def click_user_github(user_github_client_id, user_github_client_secret):
    global GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET

    GITHUB_CLIENT_ID = user_github_client_id
    GITHUB_CLIENT_SECRET = user_github_client_secret


class User(BaseUser):
    method = "github"
    routes = web.RouteTableDef()

    def __init__(self, redirect_uri, code_challenge):
        super().__init__(redirect_uri, code_challenge)

        if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
            raise Exception("GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET should be set via environment")

        self._github = GithubClient(client_id=GITHUB_CLIENT_ID, client_secret=GITHUB_CLIENT_SECRET)

    def get_authorize_page(self):
        # Chance on collision is really low, but would be really annoying. So
        # simply protect against it by looking for an unused UUID.
        state = secrets.token_hex(16)
        while state in _github_states:
            state = secrets.token_hex(16)
        self._state = state

        _github_states[self._state] = self

        # We don't set any scope, as we only want the username + id
        authorize_url = self._github.get_authorize_url(state=self._state)
        return web.HTTPFound(location=authorize_url)

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

    def _forget_github_state(self):
        if self._state:
            del _github_states[self._state]

        self._state = None

    async def get_user_information(self, code):
        # Validate the code and fetch the user info
        await self._github.get_access_token(code)
        user, _ = await self._github.user_info()

        self.display_name = user.username
        self.id = str(user.id)

    @staticmethod
    @routes.get("/user/github-callback")
    async def login_github_callback(request):
        code = in_query_github_code(request.query.get("code"))
        state = in_query_github_state(request.query.get("state"))

        user = User.get_by_state(state)
        if user is None:
            return web.HTTPNotFound()

        await user.get_user_information(code)

        return web.HTTPFound(location=f"{user.redirect_uri}?code={user.code}")

    @staticmethod
    def get_description():
        return "Login via GitHub"

    @staticmethod
    def get_settings_url():
        return f"https://github.com/settings/connections/applications/{GITHUB_CLIENT_ID}"
