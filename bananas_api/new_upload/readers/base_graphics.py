from ...helpers.enums import PackageType
from .helpers.base_sets import BaseSet


class BaseGraphics(BaseSet):
    package_type = PackageType.BASE_GRAPHICS

    INI_VALIDATION = {
        "metadata": {
            "name": str,
            "shortname": str,
            "version": str,
            "description": str,
            "palette": str,
            "blitter": str,
        },
        "files": {
            "base": str,
            "logos": str,
            "arctic": str,
            "toyland": str,
            "tropical": str,
            "extra": str,
        },
        "md5s": list,
        "origin": {
            "default": str,
        },
    }
