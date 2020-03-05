from aiohttp import web

from ..helpers.api_schema import (
    UserLogin,
    UserProfile,
)
from ..helpers.user_session import create_user_with_method
from ..helpers.web_routes import (
    in_header_authorization,
    in_query_login_method,
    in_query_login_redirect_uri,
)

routes = web.RouteTableDef()


@routes.get("/user/login")
async def login(request):
    method = in_query_login_method(request.query.get("method"))
    redirect_uri = in_query_login_redirect_uri(request.query.get("redirect-uri"))

    user, bearer_token = create_user_with_method(method, redirect_uri)
    authorize_url = user.get_authorize_url()

    user_login = UserLogin().dump({"authorize_url": authorize_url, "bearer_token": bearer_token})
    return web.json_response(user_login)


@routes.get("/user/logout")
async def logout(request):
    user = in_header_authorization(request.headers)
    user.logout()

    return web.HTTPNoContent()


@routes.get("/user")
async def profile(request):
    user = in_header_authorization(request.headers)

    user_profile = UserProfile().dump({"display_name": user.display_name})
    return web.json_response(user_profile)
