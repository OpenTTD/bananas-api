from aiohttp import web

from ..helpers.api_schema import (
    ConfigBranch,
    ConfigLicense,
    ConfigUserAudience,
)
from ..helpers.enums import (
    Branch,
    License,
)
from ..helpers.user_session import (
    get_user_method,
    get_user_methods,
)

routes = web.RouteTableDef()

BRANCHES = {
    Branch.VANILLA: "Vanilla OpenTTD",
    Branch.JGRPP: "JGRPP",
}
# Make sure all entries of Branch are in the dict above
assert all(branch in BRANCHES for branch in Branch)

# Available licenses should be equal to the License Enum.
# The value is if it is an active (non-deprecated) variant.
LICENSES = {
    License.GPL_v2: True,
    License.GPL_v3: True,
    License.LGPL_v2_1: True,
    License.CC_0_v1_0: True,
    License.CC_BY_v3_0: True,
    License.CC_BY_SA_v3_0: True,
    License.CC_BY_NC_SA_v3_0: True,
    License.CC_BY_NC_ND_v3_0: True,
    License.CUSTOM: True,
}
# Make sure all entries of License are in the dict above
assert all(license in LICENSES for license in License)


@routes.get("/config/user-audiences")
async def config_user_audiences(request):
    methods = []
    for method_name in get_user_methods():
        method = get_user_method(method_name)
        methods.append(
            ConfigUserAudience().dump(
                {
                    "name": method_name,
                    "description": method.get_description(),
                    "settings_url": method.get_settings_url(),
                }
            )
        )
    return web.json_response(methods)


@routes.get("/config/licenses")
async def config_licenses(request):
    licenses = []
    for license, active in LICENSES.items():
        licenses.append(ConfigLicense().dump({"name": license.value, "deprecated": not active}))
    return web.json_response(licenses)


@routes.get("/config/branches")
async def config_branches(request):
    branches = []
    for branch, description in BRANCHES.items():
        branches.append(ConfigBranch().dump({"name": branch.value, "description": description}))
    return web.json_response(branches)
