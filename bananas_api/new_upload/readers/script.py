import hashlib
import logging
import re

from ..exceptions import (
    Utf8FileWithoutBomException,
    ValidationException,
)
from ...helpers.enums import PackageType

log = logging.getLogger(__name__)


def decode_line(line, is_utf8):
    if is_utf8:
        return line.decode()

    try:
        latin1_line = line.decode("latin-1")
    except UnicodeDecodeError:
        # Although not 100% true, this does cover the most likely case.
        raise Utf8FileWithoutBomException

    # Check if there are any UTF-8 characters in the string
    try:
        utf8_line = line.decode()
        # If it doesn't fail decoding, but the strings are not equal, that
        # means there was valid UTF-8 in the string (as latin-1 accepts
        # nearly everything). Tell the user about it.
        if latin1_line != utf8_line:
            raise Utf8FileWithoutBomException
    except UnicodeDecodeError:
        pass

    return latin1_line


class EntryScript:
    """
    Entry script meta data.

    @ivar md5sum: md5 checksum of script file
    @type md5sum: C{bytes}

    @ivar unique_id: Unique ID of script (aka short_name)
    @type unique_id: C{str}
    """

    def __init__(self):
        self.md5sum = None
        self.unique_id = None
        self.package_type = None

    def read(self, fp):
        """
        Read an entry script ("info.nut" or "library.nut").

        @param fp: Filepointer to read (should already be open)
        @type fp: File-like object
        """

        md5sum = hashlib.md5()

        # Bit of Python trickery to allow reading the file only once,
        # while running two completely independent functions with
        # internal state. This makes the functions easier to understand,
        # while not caching the content of the file in a variable.
        unique_id = self._read_unique_id()
        script_type = self._read_script_type()
        next(unique_id)
        next(script_type)

        # Check the BOM if we should decode in UTF-8 or latin-1. This code
        # follow the same flow as the OpenTTD client has to detect UTF-8 or
        # not. It feels a bit silly to depend on the BOM marker, but we have
        # to mimick the OpenTTD client here to be correct.
        line = fp.readline()
        md5sum.update(line)
        decode_utf8 = False
        if len(line) >= 3:
            # Check for BOM marker for UTF-8; both in LE and BE.
            # Python will take care of the endianess.
            if (line[0] == 0xEF and line[1] == 0xBB) or (line[0] == 0xBB and line[1] == 0xEF):
                decode_utf8 = True

        line = decode_line(line, decode_utf8)

        unique_id.send(line)
        script_type.send(line)

        for line in fp.readlines():
            md5sum.update(line)

            line = decode_line(line, decode_utf8)

            unique_id.send(line)
            script_type.send(line)

        unique_id.close()
        script_type.close()

        if self.unique_id is None:
            raise ValidationException("Couldn't parse file to find GetShortName() function.")
        if self.package_type is None:
            raise ValidationException("Couldn't parse file to find base class.")

        self.md5sum = md5sum.digest()

    def _read_unique_id(self):
        scanning = 0

        while True:
            line = yield

            if (
                scanning == 0
                and line.find("GetShortName") != -1
                and (line.find("//") == -1 or line.find("//") > line.find("GetShortName"))
            ):
                line = line[line.find("GetShortName") :]
                scanning = 1
            if scanning == 0:
                continue

            if scanning == 1 and line.find("{") != -1:
                line = line[line.find("{") :]
                scanning = 2
            if scanning == 2 and line.find("return") != -1:
                line = line[line.find("return") :]
                scanning = 3
            if scanning == 3 and line.find("//") != -1 and line.find("//") < line.find('"'):  # watch out for // ".."
                continue
            if scanning == 3 and line.find("/*") != -1 and line.find("/*") < line.find('"'):  # watch out for /*".."*/
                line = line[line.find("/*") + 1 :]
                scanning = 4
            if scanning == 4 and line.find("*/") != -1:
                line = line[line.find("*/") + 1 :]
                scanning = 3  # return to looking for "
            if scanning == 3 and line.find('"') != -1:
                line = line[line.find('"') + 1 :]
                scanning = 5
            if scanning == 5 and line.find('"') != -1:
                self.unique_id = line[: line.find('"')].encode()
                break

        # Make sure we keep the generator alive
        while True:
            line = yield

    def _read_script_type(self):
        while True:
            line = yield

            if re.search("extends\\s+GSInfo", line) is not None:
                self.package_type = PackageType.GAME_SCRIPT
                break
            if re.search("extends\\s+GSLibrary", line) is not None:
                self.package_type = PackageType.GAME_SCRIPT_LIBRARY
                break
            if re.search("extends\\s+AIInfo", line) is not None:
                self.package_type = PackageType.AI
                break
            if re.search("extends\\s+AILibrary", line) is not None:
                self.package_type = PackageType.AI_LIBRARY
                break

        # Make sure we keep the generator alive
        while True:
            line = yield


class Script:
    """
    Script meta data.

    @ivar md5sum: md5 checksum of script file
    @type md5sum: C{bytes}
    """

    package_type = PackageType.SCRIPT_FILES

    def __init__(self):
        self.md5sum = None

    def read(self, fp):
        """
        Read a script.

        @param fp: Filepointer to read (should already be open)
        @type fp: File-like object

        @return: True on success.
        @rtype: C{bool}
        """

        md5sum = hashlib.md5()

        # Check the BOM if we should decode in UTF-8 or latin-1. This code
        # follow the same flow as the OpenTTD client has to detect UTF-8 or
        # not. It feels a bit silly to depend on the BOM marker, but we have
        # to mimick the OpenTTD client here to be correct.
        line = fp.readline()
        md5sum.update(line)
        decode_utf8 = False
        if len(line) >= 3:
            # Check for BOM marker for UTF-8; both in LE and BE.
            # Python will take care of the endianess.
            if (line[0] == 0xEF and line[1] == 0xBB) or (line[0] == 0xBB and line[1] == 0xEF):
                decode_utf8 = True

        decode_line(line, decode_utf8)

        for line in fp.readlines():
            md5sum.update(line)

            decode_line(line, decode_utf8)

        self.md5sum = md5sum.digest()
