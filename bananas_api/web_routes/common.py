import click
import logging

from aiohttp import web
from openttd_helpers import click_helper

from ..helpers.content_save import reload_index

log = logging.getLogger(__name__)
routes = web.RouteTableDef()

RELOAD_SECRET = None


@routes.get("/healthz")
async def healthz_handler(request):
    return web.HTTPOk()


@routes.post("/reload")
async def reload(request):
    if RELOAD_SECRET is None:
        return web.HTTPNotFound()

    data = await request.json()

    if "secret" not in data:
        return web.HTTPNotFound()

    if data["secret"] != RELOAD_SECRET:
        return web.HTTPNotFound()

    reload_index()

    return web.HTTPNoContent()


@click_helper.extend
@click.option(
    "--reload-secret",
    help="Secret to allow an index reload. Always use this via an environment variable!",
)
def click_reload_secret(reload_secret):
    global RELOAD_SECRET

    RELOAD_SECRET = reload_secret
