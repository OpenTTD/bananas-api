import asyncio
import click
import ctypes
import logging
import signal

from aiohttp import web
from aiohttp.web_log import AccessLogger
from ctypes.util import find_library

from .helpers.click import click_additional_options
from .helpers.content_save import click_content_save
from .helpers.sentry import click_sentry
from .helpers.user_session import (
    click_user_session,
    register_webroutes,
)
from .new_upload.session import click_cleanup_graceperiod
from .new_upload.session_publish import click_storage
from .user.github import click_user_github
from .web_routes import (
    common,
    config,
    discover,
    fallback,
    new,
    update,
    user as web_user,
)
from .web_routes.user import click_client_file

log = logging.getLogger(__name__)

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


class ErrorOnlyAccessLogger(AccessLogger):
    def log(self, request, response, time):
        # Only log if the status was not successful
        if not (200 <= response.status < 400):
            super().log(request, response, time)


def set_death_signal():
    PR_SET_PDEATHSIG = 1

    libc = ctypes.CDLL(find_library("c"))
    libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0)


async def _run_tusd(host, tusd_port, web_port, base_path, behind_proxy=False):
    command = [
        f"tusd",
        f"--host",
        f"{host}",
        f"--port",
        f"{tusd_port}",
        f"--hooks-http",
        f"http://127.0.0.1:{web_port}/new-package/tusd-internal",
        f"--hooks-enabled-events",
        f"pre-create,post-create,post-finish",
        f"--base-path",
        f"{base_path}",
    ]
    if behind_proxy:
        command += ["--behind-proxy"]

    tusd_proc = await asyncio.create_subprocess_exec(
        command[0],
        *command[1:],
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        preexec_fn=set_death_signal,
    )
    await tusd_proc.wait()


@click_additional_options
def click_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO
    )


@click.command(context_settings=CONTEXT_SETTINGS)
@click_logging  # Should always be on top, as it initializes the logging
@click_sentry
@click.option(
    "--bind", help="The IP to bind the server to", multiple=True, default=["::1", "127.0.0.1"], show_default=True
)
@click.option("--web-port", help="Port of the web server.", default=80, show_default=True, metavar="PORT")
@click.option("--tusd-port", help="Port of the tus server.", default=1080, show_default=True, metavar="PORT")
@click.option(
    "--behind-proxy", help="Respect X-Forwarded-* and similar headers which may be set by proxies.", is_flag=True
)
@common.click_reload_secret
@click_cleanup_graceperiod
@click_storage
@click_content_save
@click_client_file
@click_user_session
@click_user_github
def main(bind, web_port, tusd_port, behind_proxy):
    """
    Start the BaNaNaS API.

    Every option can also be set via an environment variable prefixed with
    BANANAS_API_; for example:

    BANANAS_API_RELOAD_SECRET="test" python -m bananas_api
    """

    webapp = web.Application()
    webapp.add_routes(common.routes)
    webapp.add_routes(config.routes)
    webapp.add_routes(discover.routes)
    webapp.add_routes(new.routes)
    webapp.add_routes(update.routes)
    webapp.add_routes(web_user.routes)

    register_webroutes(webapp)

    # Always make sure "fallback" comes last. It has a catch-all rule.
    webapp.add_routes(fallback.routes)

    # Start tusd as part of the application
    loop = asyncio.get_event_loop()
    for host in bind:
        if ":" in host:
            host = f"[{host}]"
        loop.create_task(_run_tusd(host, tusd_port, web_port, "/new-package/tus/", behind_proxy))

    # Start aiohttp server
    web.run_app(webapp, host=bind, port=web_port, access_log_class=ErrorOnlyAccessLogger)


if __name__ == "__main__":
    main(auto_envvar_prefix="BANANAS_API")
