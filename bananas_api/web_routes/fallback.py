import logging

from aiohttp import web

log = logging.getLogger(__name__)
routes = web.RouteTableDef()


@routes.route("*", "/{tail:.*}")
async def fallback(request):
    log.warning("Unexpected URL: %s", request.url)
    return web.HTTPNotFound()
