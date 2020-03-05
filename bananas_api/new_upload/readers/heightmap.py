import hashlib

from PIL import Image

from ..exceptions import ValidationException
from ...helpers.enums import PackageType


class Heightmap:
    """
    Heightmap meta data.

    @ivar md5sum: md5 checksum of heightmap file
    @type md5sum: C{bytes}

    @ivar size: Image size
    @type size: (C{int}, C{int})
    """

    package_type = PackageType.HEIGHTMAP

    def __init__(self):
        self.md5sum = None
        self.size = (None, None)

    def read(self, fp):
        """
        Read heightmap meta data

        @param fp: Filepointer to read (should already be open)
        @type fp: File-like object
        """

        pos = fp.tell()
        md5sum = hashlib.md5()
        md5sum.update(fp.read())
        self.md5sum = md5sum.digest()
        fp.seek(pos, 0)

        try:
            im = Image.open(fp)
            self.size = im.size
        except Exception:
            raise ValidationException("File is not a valid image.")
