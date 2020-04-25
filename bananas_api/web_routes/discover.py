import copy

from aiohttp import web

from ..helpers.api_schema import (
    Package,
    Version,
)
from ..helpers.content_storage import (
    get_indexed_package,
    get_indexed_packages,
    get_indexed_version,
)
from ..helpers.web_routes import (
    in_header_authorization,
    in_path_content_type,
    in_path_unique_id,
    in_path_upload_date,
    in_query_since,
)

routes = web.RouteTableDef()


@routes.get("/package/self")
async def package_from_self(request):
    user = in_header_authorization(request.headers)

    packages = []
    for package in get_indexed_packages(user=user):
        packages.append(Package().dump(package))

    return web.json_response(packages)


@routes.get("/package/{content_type}")
async def package_by_content_type(request):
    content_type = in_path_content_type(request.match_info["content_type"])
    since = in_query_since(request.query.get("since"))

    packages = []
    for package in get_indexed_packages(content_type=content_type):
        package_data = Package().dump(package)
        # To heavily reduce bandwidth, only return the versions that are
        # available for new games.
        package_data["versions"] = [
            version
            for version in package_data["versions"]
            if version["availability"] == "new-games" and (not since or version["upload-date"] > since.isoformat())
        ]
        if len(package_data["versions"]):
            packages.append(package_data)

    return web.json_response(packages)


@routes.get("/package/{content_type}/{unique_id}")
async def package_by_unique_id(request):
    content_type = in_path_content_type(request.match_info["content_type"])
    unique_id = in_path_unique_id(request.match_info["unique_id"])

    package = get_indexed_package(content_type, unique_id)
    if not package:
        return web.HTTPNotFound()

    package = Package().dump(package)
    return web.json_response(package)


@routes.get("/package/{content_type}/{unique_id}/{upload_date}")
async def package_by_upload_date(request):
    content_type = in_path_content_type(request.match_info["content_type"])
    unique_id = in_path_unique_id(request.match_info["unique_id"])
    upload_date = in_path_upload_date(request.match_info["upload_date"])

    version = get_indexed_version(content_type, unique_id, upload_date)
    if not version:
        return web.HTTPNotFound()

    # Copy and add two fields to convert VersionMinimized to Version
    version = copy.copy(version)
    version["content_type"] = content_type
    version["unique_id"] = unique_id

    version = Version().dump(version)
    return web.json_response(version)
