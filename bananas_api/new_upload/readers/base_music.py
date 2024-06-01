from ...helpers.enums import PackageType
from .helpers.base_sets import BaseSet


class BaseMusic(BaseSet):
    package_type = PackageType.BASE_MUSIC

    INI_VALIDATION = {
        "metadata": {
            "name": str,
            "shortname": str,
            "version": str,
            "description": str,
            "url": str,
        },
        "files": {
            "theme": str,
            "old_0": str,
            "old_1": str,
            "old_2": str,
            "old_3": str,
            "old_4": str,
            "old_5": str,
            "old_6": str,
            "old_7": str,
            "old_8": str,
            "old_9": str,
            "new_0": str,
            "new_1": str,
            "new_2": str,
            "new_3": str,
            "new_4": str,
            "new_5": str,
            "new_6": str,
            "new_7": str,
            "new_8": str,
            "new_9": str,
            "ezy_0": str,
            "ezy_1": str,
            "ezy_2": str,
            "ezy_3": str,
            "ezy_4": str,
            "ezy_5": str,
            "ezy_6": str,
            "ezy_7": str,
            "ezy_8": str,
            "ezy_9": str,
        },
        "md5s": list,
        "names": list,
        "origin": {
            "default": str,
        },
    }
