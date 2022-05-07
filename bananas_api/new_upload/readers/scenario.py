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

                if tag in (
                    b"MAPT",
                    b"MAPH",
                    b"MAPO",
                    b"MAP2",
                    b"M3LO",
                    b"M3HI",
                    b"MAP5",
                    b"MAPE",
                    b"MAP7",
                    b"MAP8",
                ):
                    # Make sure we read these large chunks in smaller parts.
                    # That way, we don't waste a lot of (burst) memory for
                    # something that we only do to calculate the md5sum.
                    while size > 0:
                        reader.skip(min(size, 8192))
                        size -= min(size, 8192)
                else:
                    self.read_item_without_header(tag, -1, reader.read(size))
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
                    self.read_item_without_header(tag, index, reader.read(size))
            elif type == 3 or type == 4:
                size = reader.gamma()[0] - 1
                fields = self.read_header(reader.read(size))

                index = -1
                while True:
                    size = reader.gamma()[0] - 1
                    if size < 0:
                        break
                    if type == 4:
                        index, index_size = reader.gamma()
                        size -= index_size
                    else:
                        index += 1
                    self.read_item(tag, fields, index, reader.read(size))
            else:
                raise ValidationException("Invalid savegame.")

        try:
            reader.uint8()
        except ValidationException:
            pass
        else:
            raise ValidationException("Junk at the end of file.")

        self.md5sum = md5sum.digest()

    def read_header(self, data):
        """
        Read a new-style savegame header, which describes what fields are in
        what order in the chunk.
        """
        reader = binreader.BinaryReader(io.BytesIO(data))

        fields = []
        while True:
            field_type = reader.uint8()
            if field_type == 0:
                break

            field_key = reader.gamma_str().decode()
            fields.append((field_type, field_key))

        return fields

    def read_field(self, field_type, reader):
        """
        Read a single field from a record.
        """
        if field_type == 1:
            value = reader.int8()
        elif field_type == 2:
            value = reader.uint8()
        elif field_type == 3:
            value = reader.int16(be=True)
        elif field_type == 4:
            value = reader.uint16(be=True)
        elif field_type == 5:
            value = reader.int32(be=True)
        elif field_type == 6:
            value = reader.uint32(be=True)
        elif field_type == 7:
            value = reader.int64(be=True)
        elif field_type == 8:
            value = reader.uint64(be=True)
        elif field_type == 9:
            value = reader.uint32(be=True)
        else:
            raise ValidationException("Invalid savegame.")

        return value

    def read_table(self, fields, reader):
        """
        Read a new-style savegame chunk, where the chunk started with a header.
        """
        table = {}
        for field_type, field_key in fields:
            is_list = field_type & 0x10
            field_type = field_type & 0x0F

            if field_type == 10:
                value = reader.gamma_str().decode()
            elif field_type == 11:
                size, _ = reader.gamma()
                value = reader.read(size)
            elif is_list:
                count, _ = reader.gamma()
                value = [self.read_field(field_type, reader) for _ in range(count)]
            else:
                value = self.read_field(field_type, reader)

            table[field_key] = value

        return table

    def read_item(self, tag, fields, index, data):
        """
        Read a new-style savegame chunk, where the chunk started with a header.
        """
        reader = binreader.BinaryReader(io.BytesIO(data))

        # Only look at those chunks that have data we are interested in.
        if tag not in (b"MAPS", b"NGRF", b"AIPL", b"GSDT"):
            return

        table = self.read_table(fields, reader)

        if tag == b"MAPS":
            self.map_size = (table["dim_x"], table["dim_y"])
        elif tag == b"NGRF":
            self.newgrf.append(
                (table["ident.grfid"], bytes(table["ident.md5sum"]).hex(), table["version"], table["filename"])
            )
        elif tag == b"AIPL":
            if table["is_random"] == 0 and table["name"]:
                self.ai.append((None, None, table["version"], table["name"]))
        elif tag == b"GSDT":
            if table["is_random"] == 0 and table["name"]:
                self.gs.append((None, None, table["version"], table["name"]))

    def read_item_without_header(self, tag, index, data):
        """
        Read a old-style savegame chunk, where the chunk started without a header.
        """

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
