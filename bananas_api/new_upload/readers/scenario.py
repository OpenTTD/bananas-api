import hashlib
import io
import lzma
import zlib

from ...helpers.enums import PackageType
from ..exceptions import ValidationException
from .helpers import binreader


class PlainFile:
    @staticmethod
    def open(f):
        return f


class ZLibFile:
    @staticmethod
    def open(f):
        return ZLibFile(f)

    def __init__(self, file):
        self.file = file
        self.decompressor = zlib.decompressobj()
        self.uncompressed = bytearray()

    def close(self):
        pass

    def read(self, amount):
        while len(self.uncompressed) < amount:
            new_data = self.file.read(8192)
            if len(new_data) == 0:
                break
            self.uncompressed += self.decompressor.decompress(new_data)

        data = self.uncompressed[0:amount]
        self.uncompressed = self.uncompressed[amount:]
        return data


UNCOMPRESS = {
    b"OTTN": PlainFile,
    b"OTTZ": ZLibFile,
    b"OTTX": lzma,
    # Although OpenTTD supports lzo2, it is very difficult to load this in
    # Python. Additionally, no savegame ever uses this format (OTTN is
    # prefered over OTTD, which requires no additional libraries in the
    # OpenTTD client), unless a user specificly switches to it. As such,
    # it is reasonably enough to simply refuse this compression format.
    # b"OTTD": lzo2,
}


class Scenario:
    """
    Scenario meta data.

    It really is a savegame, but we name it scenario in BaNaNaS.

    @ivar md5sum: md5 checksum of compressed savegame
    @type md5sum: C{bytes}

    @ivar savegame_version: Savegame version
    @type savegame_version: C{int}

    @ivar map_size: Map size
    @type map_size: (C{int}, c{int})

    @ivar newgrf: List of NewGRF as (grf-id, md5sum, version, filename)
    @type newgrf: C{list} of (C{int}, C{str}, C{int}, C{str})

    @ivar ai: List of non-random AIs as (short-id, md5sum, version, name)
    @type ai: C{list} of (C{None}, C{None}, C{int}, C{str})

    @ivar gs: List of game scripts as (short-id, md5sum, version, name)
    @type gs: C{list} of (C{None}, C{None}, C{int}, C{str})
    """

    package_type = PackageType.SCENARIO

    def __init__(self):
        self.md5sum = None
        self.savegame_version = None
        self.map_size = (None, None)
        self.newgrf = []
        self.ai = []
        self.gs = []

    def read(self, fp):
        """
        Read savegame meta data.

        @param fp: Filepointer to read (should already be open)
        @type fp: File-like object
        """

        md5sum = hashlib.md5()
        reader = binreader.BinaryReader(fp, md5sum)

        compression = reader.read(4)
        self.savegame_version = reader.uint16(be=True)
        reader.uint16()

        decompressor = UNCOMPRESS.get(compression)
        if decompressor is None:
            raise ValidationException(f"Unknown savegame compression {compression}.")

        uncompressed = decompressor.open(reader)
        reader = binreader.BinaryReader(uncompressed)

        while True:
            tag = reader.read(4)
            if len(tag) == 0 or tag == b"\0\0\0\0":
                break
            if len(tag) != 4:
                raise ValidationException("Invalid savegame.")

            type = reader.uint8()
            if (type & 0x0F) == 0x00:
                size = type << 20 | reader.uint24(be=True)
                self.read_item(tag, -1, reader.read(size))
            elif type == 1 or type == 2:
                index = -1
                while True:
                    size = reader.gamma()[0] - 1
                    if size < 0:
                        break
                    if type == 2:
                        index, index_size = reader.gamma()
                        size -= index_size
                    else:
                        index += 1
                    self.read_item(tag, index, reader.read(size))

        try:
            reader.uint8()
        except ValidationException:
            pass
        else:
            raise ValidationException("Junk at the end of file.")

        self.md5sum = md5sum.digest()

    def read_item(self, tag, index, data):
        reader = binreader.BinaryReader(io.BytesIO(data))

        if tag == b"MAPS":
            size_x = reader.uint32(be=True)
            size_y = reader.uint32(be=True)
            self.map_size = (size_x, size_y)
        elif tag == b"NGRF":
            filename = reader.gamma_str().decode()
            grfid = reader.uint32(be=True)
            md5sum = reader.read(16).hex()
            if self.savegame_version < 151:
                version = None
            else:
                version = reader.uint32(be=True)
            self.newgrf.append((grfid, md5sum, version, filename))
        elif tag == b"AIPL":
            name = reader.gamma_str().decode()
            reader.gamma_str()
            if self.savegame_version < 108:
                version = None
            else:
                version = reader.uint32(be=True)
            is_random = self.savegame_version >= 136 and reader.uint8() != 0
            if not is_random and len(name) > 0:
                self.ai.append((None, None, version, name))
        elif tag == b"GSDT":
            name = reader.gamma_str().decode()
            reader.gamma_str()
            version = reader.uint32(be=True)
            is_random = reader.uint8() != 0
            if not is_random and len(name) > 0:
                self.gs.append((None, None, version, name))
