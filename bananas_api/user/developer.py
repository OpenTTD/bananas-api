from aiohttp import web

from .base import User as BaseUser
from ..helpers.user_session import get_user_by_code

# !!!!!!!
# WARNING - Never use this in production. It allows anyone to login as anyone
# !!!!!!!


class User(BaseUser):
    method = "developer"
    routes = web.RouteTableDef()

    def get_authorize_page(self):
        return web.json_response({"developer-code": self.code})

    def force_login(self, username):
        self.id = username
        self.display_name = username

    @staticmethod
    @routes.post("/user/developer")
    async def login_github_callback(request):
        data = await request.json()

        username = data["username"]
        code = data["code"]

        user = get_user_by_code(code)
        user.force_login(username)

        return web.HTTPFound(location=f"{user.redirect_uri}?code={user.code}")
