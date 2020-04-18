import base64
import logging
import os

from aiohttp import web
from marshmallow.exceptions import ValidationError

from ..helpers.api_schema import (
    normalize_message,
    UploadNew,
    UploadStatus,
    VersionMinimized,
)
from ..helpers.enums import Status
from ..helpers.web_routes import (
    in_header_authorization,
    in_path_file_uuid,
    in_path_upload_token,
    JSONException,
)
from ..new_upload.exceptions import ValidationException
from ..new_upload.session import (
    add_file,
    create_token,
    get_session,
    get_session_by_token,
    publish_session,
    update_session,
    validate_session,
)

log = logging.getLogger(__name__)
routes = web.RouteTableDef()


@routes.post("/new-package/tusd-internal")
async def tusd_handler(request):
    if request.remote != "127.0.0.1":
        return web.HTTPNotFound()

    payload = await request.json()
    headers = payload["HTTPRequest"]["Header"]
    # 'headers' is a dict of lists, where aiohttp only shows the last value.
    # So flatten the headers, and only pick the last header per key given.
    # Example: { "Upload-Length": [ 12 ] } becomes { "Upload-Length": 12 }.
    headers = {k: v[-1] for k, v in headers.items()}

    hook_name = request.headers.get("Hook-Name")
    if hook_name == "pre-create":
        if "Upload-Metadata" not in headers:
            return web.json_response({"message": "no filename given in metadata"}, status=400)

        # MetaData is stored overly complex: in a single header, comma
        # separated per key-value pair, which is stored space separated. On
        # top of that, the value is base64 encoded. In other words:
        # "key base64-value,key base64-value,.."
        try:
            metadata = dict([e.split(" ") for e in headers.get("Upload-Metadata", "").split(",")])
            for key, value in metadata.items():
                metadata[key] = base64.b64decode(value).decode()
        except Exception:
            raise JSONException({"message": "Upload-Metadata header is invalid"})

        if not metadata.get("filename"):
            return web.json_response({"message": "no filename given in metadata"}, status=400)

        if not metadata.get("upload-token"):
            return web.json_response({"message": "no upload-token given in metadata"}, status=400)

        upload_token = in_path_upload_token(metadata.get("upload-token"))

        session = get_session_by_token(upload_token)
        if session is None:
            return web.HTTPNotFound()

        return web.HTTPOk()

    if hook_name in ("post-create", "post-finish"):
        payload = await request.json()

        upload_token = in_path_upload_token(payload["Upload"]["MetaData"]["upload-token"])

        session = get_session_by_token(upload_token)
        if session is None:
            return web.HTTPNotFound()

        if hook_name == "post-create":
            announcing = True
        else:
            announcing = False

        add_file(
            session,
            payload["Upload"]["ID"],
            payload["Upload"]["MetaData"]["filename"],
            payload["Upload"]["Size"],
            payload["Upload"]["Storage"]["Path"],
            announcing=announcing,
        )

        return web.HTTPOk()

    log.warning("Unexpected hook-name: %s", hook_name)
    return web.HTTPNotFound()


@routes.post("/new-package")
async def new_start(request):
    user = in_header_authorization(request.headers)

    token = create_token(user)

    payload = UploadNew().dump({"upload_token": str(token)})
    return web.json_response(payload)


@routes.get("/new-package/{upload_token}")
async def new_status(request):
    upload_token = in_path_upload_token(request.match_info["upload_token"])
    user = in_header_authorization(request.headers)

    session = get_session(user, upload_token)
    if session is None:
        return web.HTTPNotFound()

    validate_session(session)

    upload_status = UploadStatus().dump(session)
    return web.json_response(upload_status)


@routes.put("/new-package/{upload_token}")
async def new_update(request):
    upload_token = in_path_upload_token(request.match_info["upload_token"])
    user = in_header_authorization(request.headers)

    session = get_session(user, upload_token)
    if session is None:
        return web.HTTPNotFound()

    try:
        data = VersionMinimized(dump_only=VersionMinimized.read_only_for_new).load(await request.json())
    except ValidationError as e:
        return web.json_response(
            {"message": "request body failed validation", "errors": normalize_message(e)}, status=400
        )

    try:
        update_session(session, data)
    except ValidationException as e:
        return web.json_response({"message": "request body failed validation", "errors": e.args[0]}, status=400)

    return web.HTTPNoContent()


@routes.delete("/new-package/{upload_token}/{file_uuid}")
async def new_delete_file(request):
    upload_token = in_path_upload_token(request.match_info["upload_token"])
    file_uuid = in_path_file_uuid(request.match_info["file_uuid"])
    user = in_header_authorization(request.headers)

    session = get_session(user, upload_token)
    if session is None:
        return web.HTTPNotFound()

    for file_info in session["files"]:
        if file_info["uuid"] == file_uuid:
            internal_filename = file_info["internal_filename"]
            os.remove(internal_filename)
            os.remove(f"{internal_filename}.info")
            session["files"].remove(file_info)
            break
    else:
        return web.HTTPNotFound()

    return web.HTTPNoContent()


@routes.post("/new-package/{upload_token}/publish")
async def new_publish(request):
    upload_token = in_path_upload_token(request.match_info["upload_token"])
    user = in_header_authorization(request.headers)

    session = get_session(user, upload_token)
    if session is None:
        return web.HTTPNotFound()

    validate_session(session)

    if session["status"] == Status.ERRORS:
        errors = session["errors"]
        return web.json_response({"message": "package has validation errors", "errors": errors}, status=400)

    publish_session(session)

    upload_status = UploadStatus().dump(session)
    return web.json_response(upload_status, status=201)
