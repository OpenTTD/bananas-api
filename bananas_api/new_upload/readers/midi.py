import hashlib

from ...helpers.enums import PackageType
from ..exceptions import ValidationException
from .helpers import binreader


class Midi:
    """
    Midi meta data.

    @ivar md5sum: md5 checksum of midi file
    @type md5sum: C{bytes}
    """

    package_type = PackageType.MUSIC_FILES

    def __init__(self):
        self.md5sum = None

    def read(self, fp):
        """
        Read midi meta data.

        @param fp: Filepointer to read (should already be open)
        @type fp: File-like object
        """

        md5sum = hashlib.md5()
        reader = binreader.BinaryReader(fp, md5sum)

        header = reader.read(8)
        if header != b"MThd\x00\x00\x00\x06":
            raise ValidationException("Invalid MIDI header.")

        # Read the rest to complete the md5sum
        reader.read(None)
        self.md5sum = md5sum.digest()
