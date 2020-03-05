import hashlib

from ...helpers.enums import PackageType
from ..exceptions import ValidationException
from .helpers import binreader


class Cat:
    """
    Cat meta data.

    @ivar md5sum: md5 checksum of cat file
    @type md5sum: C{bytes}
    """

    package_type = PackageType.SOUND_FILES

    def __init__(self):
        self.md5sum = None

    def read(self, fp):
        """
        Read cat meta data.

        @param fp: Filepointer to read (should already be open)
        @type fp: File-like object
        """

        md5sum = hashlib.md5()
        reader = binreader.BinaryReader(fp, md5sum)

        header = reader.uint32()
        # Because .cat files have a fixed set of samples, we know the "header",
        # which in reality is the amount of entries times 8, and a flag.
        if header not in (0x80000248, 0x00000248):
            raise ValidationException("Invalid cat header.")

        # Read the rest to complete the md5sum
        reader.read(None)
        self.md5sum = md5sum.digest()
