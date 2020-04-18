import asyncio
import click
import logging
import os
import secrets

from collections import defaultdict

from .exceptions import ValidationException
from .session_publish import (
    create_package,
    create_tarball,
)
from .session_validation import (
    validate_has_access,
    validate_is_valid_package,
    validate_license,
    validate_new_package,
    validate_packet_size,
    validate_unique_md5sum_partial,
    validate_unique_version,
    validate_version,
)
from .validate import validate_files
from ..helpers.click import click_additional_options
from ..helpers.content_storage import get_indexed_package
from ..helpers.enums import Status

log = logging.getLogger(__name__)

KEYS_ALLOWED_TO_UPDATE = {"version", "license", "dependencies", "compatibility", "name", "description", "url", "tags"}
TIMER_TIMEOUT = 60 * 15

_timer = defaultdict(lambda: None)
_sessions = {}
_tokens = {}


def cleanup_session(session):
    if _timer[session["user"].full_id]:
        _timer[session["user"].full_id].cancel()
        _timer[session["user"].full_id] = None

    for file_info in session["announced-files"].values():
        os.unlink(file_info["internal_filename"])
        os.unlink(f"{file_info['internal_filename']}.info")

    for file_info in session["files"]:
        os.unlink(file_info["internal_filename"])
        os.unlink(f"{file_info['internal_filename']}.info")

    del _tokens[session["token"]]
    del _sessions[session["user"].full_id]


async def _timer_handler(session):
    await asyncio.sleep(TIMER_TIMEOUT)

    _timer[session["user"].full_id] = None
    cleanup_session(session)


def reset_session_timer(session, first_time=False):
    if not first_time:
        if not _timer[session["user"].full_id]:
            log.error("Tried to reset a timer of a session that is already expired")
            return

        _timer[session["user"].full_id].cancel()

    # Per user, start a timer. If it expires, we remove the cnontent. This
    # means that if a user failed to publish within a reasonable amount of
    # time, we reclaim the diskspace.
    loop = asyncio.get_event_loop()
    _timer[session["user"].full_id] = loop.create_task(_timer_handler(session))


@click_additional_options
@click.option(
    "--cleanup-graceperiod",
    help="Graceperiod between cleanup of new uploads.",
    default=60 * 15,
    show_default=True,
    metavar="SECONDS",
)
def click_cleanup_graceperiod(cleanup_graceperiod):
    global TIMER_TIMEOUT
    TIMER_TIMEOUT = cleanup_graceperiod


def create_token(user):
    if user.full_id in _sessions:
        cleanup_session(_sessions[user.full_id])

    # Change on collision is really low, but would be really annoying. So
    # simply protect against it by looking for an unused UUID.
    token = secrets.token_hex(16)
    while token in _tokens:
        token = secrets.token_hex(16)

    session = {
        "user": user,
        "token": token,
        "status": Status.OK,
        "errors": [],
        "warnings": [],
        "files": [],
        "announced-files": {},
    }
    _sessions[user.full_id] = session
    _tokens[token] = user

    reset_session_timer(session, first_time=True)

    return token


def get_session(user, token):
    if user.full_id not in _sessions:
        return

    if _sessions[user.full_id]["token"] != token:
        return

    session = _sessions[user.full_id]
    reset_session_timer(session)

    return session


def get_session_by_token(token):
    if token not in _tokens:
        return

    user = _tokens[token]
    return get_session(user, token)


def validate_session(session):
    session["errors"] = []
    session["warnings"] = []

    try:
        data = validate_files(session["files"])
    except ValidationException as e:
        session["errors"].append(e.args[0])
        data = None

    for file_info in session["files"]:
        if file_info["errors"]:
            session["errors"].append(f"File '{file_info['filename']}' failed validation")

            for error in file_info["errors"]:
                session["errors"].append(f"{file_info['filename']}: {error}")

    validate_is_valid_package(session, data)
    validate_license(session)
    validate_version(session)

    if "content_type" in session:
        package = get_indexed_package(session["content_type"], session["unique_id"])
    else:
        package = None

    if package:
        validate_has_access(session, package)
        validate_unique_version(session, package)
        validate_unique_md5sum_partial(session, package)
        validate_packet_size(session, package)
    else:
        validate_new_package(session)
        validate_packet_size(session, {})

    if session["errors"]:
        session["status"] = Status.ERRORS
    elif session["warnings"]:
        session["status"] = Status.WARNINGS
    else:
        session["status"] = Status.OK


def add_file(session, uuid, filename, filesize, internal_filename, announcing=False):
    new_file = {
        "uuid": uuid,
        "filename": filename,
        "filesize": filesize,
        "internal_filename": internal_filename,
        "errors": [],
    }

    if announcing:
        # For very small files, "post-finish" is called before "post-create"
        # by tusd. In result, announcing is done after the file is added. So
        # simply check if we already know about it, and ignore if this is the
        # case.
        for file_info in session["files"]:
            if file_info["uuid"] == uuid:
                return

        session["announced-files"][uuid] = new_file
    else:
        if uuid in session["announced-files"]:
            del session["announced-files"][uuid]

        session["files"].append(new_file)


def update_session(session, data):
    # This should never happen, as "data" should already be validated. But
    # because this can have a huge impact, make sure we are absolutely sure.
    if set(data.keys()) - KEYS_ALLOWED_TO_UPDATE:
        raise Exception(
            "Internal error: tried to update keys that are not allowed to be updated: %r"
            % (set(data.keys()) - KEYS_ALLOWED_TO_UPDATE)
        )

    for key, value in data.items():
        if isinstance(value, str):
            session[key] = value.strip()
        else:
            session[key] = value


def publish_session(session):
    create_tarball(session)
    create_package(session)
    cleanup_session(session)
