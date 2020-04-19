from aiohttp import web

from ..helpers.api_schema import (
    UserToken,
    UserProfile,
)
from ..helpers.user_session import (
    create_user_with_method,
    get_user_by_code,
)
from ..helpers.web_routes import (
    in_header_authorization,
    in_query_authorize_audience,
    in_query_authorize_code_challenge_method,
    in_query_authorize_redirect_uri,
    in_query_authorize_response_type,
    in_post_token_code,
    in_post_token_grant_type,
    in_post_token_redirect_uri,
)

routes = web.RouteTableDef()


@routes.get("/user/authorize")
async def login(request):
    audience = in_query_authorize_audience(request.query.get("audience"))
    in_query_authorize_response_type(request.query.get("response_type"))
    client_id = request.query.get("client_id")
    redirect_uri = in_query_authorize_redirect_uri(request.query.get("redirect_uri"))
    code_challenge = request.query.get("code_challenge")  # TODO -- Length check
    in_query_authorize_code_challenge_method(request.query.get("code_challenge_method"))

    # TODO -- Check if client_id exists
    # TODO -- Check if redirect_uri is allowed with client_id
    client_id

    user = create_user_with_method(audience, redirect_uri, code_challenge)
    return user.get_authorize_page()


@routes.post("/user/token")
async def oauth_token(request):
    payload = await request.json()

    client_id = payload.get("client_id")
    code_verifier = payload.get("code_verifier")  # TODO -- Length check (min / max)
    code = in_post_token_code(payload.get("code"))
    redirect_uri = in_post_token_redirect_uri(payload.get("redirect_uri"))
    in_post_token_grant_type(payload.get("grant_type"))

    # TODO -- Check if client_id exists
    client_id

    user = get_user_by_code(code)
    if user is None:
        return web.HTTPNotFound()

    if user.redirect_uri != redirect_uri:
        return web.HTTPNotFound()

    if not user.validate(code_verifier):
        return web.HTTPNotFound()

    user_login = UserToken().dump({"access_token": user.bearer_token, "token_type": "Bearer"})
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
