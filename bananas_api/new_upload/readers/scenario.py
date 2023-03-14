import enum
import hashlib
import io
import lzma
import zlib

from ...helpers.enums import PackageType
from ..exceptions import ValidationException
from .helpers import binreader


@enum.unique
class Landscape(enum.IntEnum):
    TEMPERATE = 0
    ARCTIC = 1
    TROPIC = 2
    TOYLAND = 3


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

    @ivar histogram: List of 256 entries indicating how often that height level occurs
    @type histogram: C{list} of C{int}

    @ivar newgrf: List of NewGRF as (grf-id, md5sum, version, filename)
    @type newgrf: C{list} of (C{int}, C{str}, C{int}, C{str})

    @ivar ai: List of non-random AIs as (short-id, md5sum, version, name)
    @type ai: C{list} of (C{None}, C{None}, C{int}, C{str})

    @ivar gs: List of game scripts as (short-id, md5sum, version, name)
    @type gs: C{list} of (C{None}, C{None}, C{int}, C{str})

    @ivar landscape: Landscape type
    @type landscape: C{int}
    """

    package_type = PackageType.SCENARIO

    def __init__(self):
        self.md5sum = None
        self.savegame_version = None
        self.is_patchpack = None
        self.map_size = (None, None)
        self.histogram = None
        self.newgrf = []
        self.ai = []
        self.gs = []
        self.landscape = None

        # In old savegames, heightmap was in MAPT. In newer in MAPH.
        # So we assume MAPH, but if that means histogram remains empty,
        # we use MAPT. That way, the new purpose of those bits in MAPT
        # aren't influencing the histogram.
        self._histogram_old = None

    def read(self, fp):
        """
        Read savegame meta data.

        @param fp: Filepointer to read (should already be open)
        @type fp: File-like object
        """

        md5sum = hashlib.md5()
        reader = binreader.BinaryReader(fp, md5sum)

        compression = reader.read(4)
        savegame_version = reader.uint16(be=True)
        self.savegame_version = savegame_version & 0xFFF
        self.is_patchpack = savegame_version & 0x8000 != 0
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

            # JGRPP's extended header
            if (type & 0x0F) == 0x0F:
                ext_flags = reader.uint32(be=True)
                type = reader.uint8()
            else:
                ext_flags = 0

            if (type & 0x0F) == 0x00:
                size = type << 20 | reader.uint24(be=True)

                # JGRPP's big RIFF flag
                if ext_flags & 0x01:
                    size += reader.uint32(be=True) << 28

                # New savegame format, with the height of the tile in MAPH.
                if tag == b"MAPH":
                    self.histogram = [0] * 256
                    while size > 0:
                        data = reader.read(min(size, 8192))
                        for h in data:
                            self.histogram[h] += 1
                        size -= min(size, 8192)

                # Old savegame format, with the height of the tile in MAPT.
                if tag == b"MAPT":
                    self._histogram_old = [0] * 256
                    while size > 0:
                        data = reader.read(min(size, 8192))
                        for h in data:
                            self._histogram_old[h & 0xF] += 1
                        size -= min(size, 8192)

                # JGRPP-based map chunk containing the height of the tile.
                if tag == b"WMAP":
                    self.histogram = [0] * 256

                    # First chunk is 8 bytes per tile for the whole map.
                    chunk_map_size = self.map_size[0] * self.map_size[1] * 8
                    if chunk_map_size > size:
                        raise ValidationException("Invalid savegame.")

                    # Read this first chunk.
                    while chunk_map_size > 0:
                        data = reader.read(min(chunk_map_size, 8192))

                        for i in range(0, len(data), 8):
                            # Height is the second byte in the tile.
                            h = data[i + 1]
                            self.histogram[h] += 1

                        chunk_map_size -= min(chunk_map_size, 8192)
                        size -= min(size, 8192)

                    # There can be other tile-data after the first chunk; skip this.
                    while size > 0:
                        reader.skip(min(size, 8192))
                        size -= min(size, 8192)

                if tag in (
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
            v = reader.uint8()
        except ValidationException:
            pass
        else:
            # Savegames before r20090 could contain a junk-block of 128 KiB of all zeros.
            if v == 0:
                for _ in range(128 * 1024 - 1):
                    try:
                        v = reader.uint8()
                    except ValidationException:
                        # In case it is not a block of 128 KiB, it is junk.
                        raise ValidationException("Junk at the end of file.")

                    # In case it is not a zero, it is junk.
                    if v != 0:
                        raise ValidationException("Junk at the end of file.")
            else:
                raise ValidationException("Junk at the end of file.")

        # Savegames before version 6 had no MAPS chunk, and are always 256x256.
        if self.savegame_version < 6:
            self.map_size = (256, 256)

        if self.map_size[0] is None:
            raise ValidationException("Scenario is missing essential chunks (MAPS).")
        if self.histogram is None:
            if self._histogram_old is None:
                raise ValidationException("Scenario is missing essential chunks (MAPT / MAPH).")
            else:
                self.histogram = self._histogram_old

        if self.map_size[0] * self.map_size[1] == self.histogram[0]:
            raise ValidationException("Map is completely empty.")

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
        if tag not in (b"MAPS", b"NGRF", b"AIPL", b"GSDT", b"PATS"):
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
        elif tag == b"PATS":
            self.landscape = table["game_creation.landscape"]

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
        elif tag == b"PATS":
            # Before version 97, landscape was part not part of OPTS.
            if self.savegame_version < 97:
                return

            # Various of difficulty-related settings.
            reader.skip(19)

            # Subsidy-duration setting.
            if self.savegame_version >= 292:
                reader.skip(2)

            # Difficulty-level setting.
            if self.savegame_version < 178:
                reader.skip(1)

            # Competitor-start-time and competitor-speed settings.
            if self.savegame_version >= 97 and self.savegame_version < 110:
                reader.skip(2)

            reader.skip(1)  # town-name setting.
            self.landscape = Landscape(reader.uint8())
        elif tag == b"OPTS":
            if self.savegame_version < 4:
                reader.skip(17 * 2)  # Difficulty-custom settings.
            else:
                reader.skip(18 * 2)
            reader.skip(1)  # Difficulty-level setting.
            reader.skip(1)  # Currency setting.
            reader.skip(1)  # Units setting.
            reader.skip(1)  # Town-name setting.
            self.landscape = Landscape(reader.uint8())
