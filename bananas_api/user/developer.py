from aiohttp import web

from .base import User as BaseUser
from ..helpers.web_routes import in_header_authorization_pre

# !!!!!!!
# WARNING - Never use this in production. It allows anyone to login as anyone
# !!!!!!!


class User(BaseUser):
    method = "developer"
    routes = web.RouteTableDef()

    def get_authorize_url(self):
        return None

    def force_login(self, username):
        self.id = username
        self.display_name = username

    @staticmethod
    @routes.post("/user/developer")
    async def login_github_callback(request):
        user = in_header_authorization_pre(request.headers)

        data = await request.json()
        username = data["username"]
        user.force_login(username)

        return web.HTTPNoContent()
