import hashlib

import _bananas_api

from ..exceptions import ValidationException
from ...helpers.enums import PackageType


def rgb_to_gray(color):
    return ((color[0] * 19595) + (color[1] * 38470) + (color[2] * 7471)) // 65536


class Heightmap:
    """
    Heightmap meta data.

    @ivar md5sum: md5 checksum of heightmap file
    @type md5sum: C{bytes}

    @ivar size: Image size
    @type size: (C{int}, C{int})

    @ivar histogram: List of 256 entries indicating how often that height level occurs
    @type histogram: C{list} of C{int}
    """

    package_type = PackageType.HEIGHTMAP

    def __init__(self):
        self.md5sum = None
        self.size = (None, None)
        self.histogram = None

    def read(self, fp):
        """
        Read heightmap meta data

        @param fp: Filepointer to read (should already be open)
        @type fp: File-like object
        """

        image_data = fp.read()

        md5sum = hashlib.md5()
        md5sum.update(image_data)
        self.md5sum = md5sum.digest()

        info = _bananas_api.heightmap(image_data)
        if info["error"]:
            raise ValidationException(info["error"])

        if sum(info["histogram"]) != info["width"] * info["height"]:
            print(sum(info["histogram"]), info["width"] * info["height"])
            raise ValidationException("Histogram does not match image size")

        self.size = (info["width"], info["height"])
        self.histogram = info["histogram"]
