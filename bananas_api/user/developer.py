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
        # assume developer auth happens on http and not https. If it does happen to be on https,
        #  the developer should be smart enough to know how to fix the returned url by themselves.
        # While for a browser session, we could suffice with a relative url, because this url is shown in the
        #  cli for copy-pasting, we need to include the host name as well.
        authorize_url = f"http://{self.request_host}/user/developer?code={self.code}"

        return web.HTTPFound(location=authorize_url)

    @staticmethod
    @routes.get("/user/developer")
    def login_page(request):
        code = request.query.get("code")
        return web.Response(
            body="<html><body>"
            "<h1>Developer login</h1>"
            "Username:"
            "<form method=POST action='/user/developer'>"
            f"<input type='hidden' name='code' value='{code}'>"
            "<input type='text' name='username'>"
            "<input type='submit' value='Login'>"
            "</form></body></html>",
            content_type="text/html",
            headers={"Developer-Code": code},
        )

    def force_login(self, username):
        self.id = username
        self.display_name = username

    @staticmethod
    @routes.post("/user/developer")
    async def login_github_callback(request):
        data = await request.text()

        payload = {}
        for key_value in data.split("&"):
            key, _, value = key_value.partition("=")
            payload[key] = value

        if "username" not in payload:
            return web.HTTPBadRequest(reason="username not defined in payload")

        username = payload["username"]
        code = payload["code"]

        user = get_user_by_code(code)
        if not user:
            return web.HTTPNotFound()
        user.force_login(username)

        return web.HTTPFound(location=f"{user.redirect_uri}?code={user.code}")

    @staticmethod
    def get_description():
        return "Login as developer"

    @staticmethod
    def get_settings_url():
        return ""
