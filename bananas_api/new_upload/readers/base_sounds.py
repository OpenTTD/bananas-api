from ...helpers.enums import PackageType
from .helpers.base_sets import BaseSet


class BaseSounds(BaseSet):
    package_type = PackageType.BASE_SOUNDS

    INI_VALIDATION = {
        "metadata": {
            "name": str,
            "shortname": str,
            "version": str,
            "description": str,
        },
        "files": {
            "samples": str,
        },
        "md5s": list,
        "origin": {
            "default": str,
        },
    }
