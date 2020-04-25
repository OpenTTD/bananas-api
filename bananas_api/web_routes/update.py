from aiohttp import web
from marshmallow.exceptions import ValidationError

from ..helpers.api_schema import (
    normalize_message,
    Global,
    VersionMinimized,
)
from ..helpers.content_save import queue_store_on_disk
from ..helpers.content_storage import (
    get_indexed_package,
    get_indexed_version,
)
from ..helpers.web_routes import (
    in_header_authorization,
    in_path_content_type,
    in_path_unique_id,
    in_path_upload_date,
)

routes = web.RouteTableDef()


@routes.put("/package/{content_type}/{unique_id}")
async def package_update(request):
    content_type = in_path_content_type(request.match_info["content_type"])
    unique_id = in_path_unique_id(request.match_info["unique_id"])
    user = in_header_authorization(request.headers)

    try:
        package = get_indexed_package(content_type, unique_id)
    except KeyError:
        return web.HTTPNotFound()

    for author in package["authors"]:
        if author.get(user.method) == user.id:
            break
    else:
        return web.HTTPNotFound()

    try:
        data = Global(dump_only=Global.read_only).load(await request.json())
    except ValidationError as e:
        return web.json_response(
            {"message": "request body failed validation", "errors": normalize_message(e)}, status=400
        )

    # The only field you are not allowed to make empty (and which you can
    # change), is "version", so do some extra validation there.
    if "name" in data and not len(data["name"].strip()):
        return web.json_response(
            {"message": "request body failed validation", "errors": {"name": ["Cannot be empty"]}}, status=400
        )

    # Update the record with the changed fields and schedule for commit
    for key, value in data.items():
        if isinstance(value, str):
            value = value.strip()
            package[key] = value

            # Setting an empty string means: use the one from global.
            if value == "":
                del package[key]
        else:
            package[key] = value

    queue_store_on_disk(user, package)

    return web.HTTPNoContent()


@routes.put("/package/{content_type}/{unique_id}/{upload_date}")
async def version_update(request):
    content_type = in_path_content_type(request.match_info["content_type"])
    unique_id = in_path_unique_id(request.match_info["unique_id"])
    upload_date = in_path_upload_date(request.match_info["upload_date"])
    user = in_header_authorization(request.headers)

    try:
        package = get_indexed_package(content_type, unique_id)
    except KeyError:
        return web.HTTPNotFound()

    for author in package["authors"]:
        if author.get(user.method) == user.id:
            break
    else:
        return web.HTTPNotFound()

    try:
        version = get_indexed_version(content_type, unique_id, upload_date)
    except KeyError:
        return web.HTTPNotFound()

    try:
        data = VersionMinimized(dump_only=VersionMinimized.read_only).load(await request.json())
    except ValidationError as e:
        return web.json_response(
            {"message": "request body failed validation", "errors": normalize_message(e)}, status=400
        )

    # The only field you are not allowed to make empty (and which you can
    # change), is "version", so do some extra validation there.
    if "version" in data and not len(data["version"].strip()):
        return web.json_response(
            {"message": "request body failed validation", "errors": {"version": ["Cannot be empty"]}}, status=400
        )

    # Update the record with the changed fields and schedule for commit
    for key, value in data.items():
        if isinstance(value, str):
            value = value.strip()
            version[key] = value

            # Setting an empty string means: use the one from global.
            if value == "":
                del version[key]
        else:
            version[key] = value

    queue_store_on_disk(user, package)

    return web.HTTPNoContent()
