from configparser import ConfigParser

from ...exceptions import ValidationException


class BaseSet:
    """
    Base Set inifile meta data.

    @ivar md5sum: md5 checksum of NewGRFs in Base Set inifile
    @type md5sum: C{bytes}

    @ivar unique_id: Unique ID of Base Set
    @type unique_id: C{str}

    @ivar version: Version of Base Set
    @type version: C{str}

    @ivar description: Description of Base Set
    @type description: C{str}

    @ivar files: Files included in Base Set, with their md5sum
    @type files: C{dict}
    """

    INI_VALIDATION = None

    def __init__(self):
        self.md5sum = None
        self.unique_id = None
        self.version = None
        self.description = None
        self.files = None

    def read(self, fp):
        """
        Read Base Set inifile meta data

        @param fp: Filepointer to read (should already be open)
        @type fp: File-like object
        """
        content = fp.read()
        content = content.decode("latin-1")

        ini_parser = ConfigParser()
        ini_parser.read_string(content)

        # Check if the ini-file has all the required bits and pieces
        for section, keys in self.INI_VALIDATION.items():
            if not ini_parser.has_section(section):
                raise ValidationException(f"Section {section} is missing")

            if not isinstance(keys, dict):
                continue

            # We support translating most entries, like "name.en_us", etc. so
            # filter those out.
            keys_in_section = [key.split(".")[0] for key in ini_parser.options(section)]
            # Check if we have entries that were not expected
            for diff in set(keys_in_section) - set(keys):
                raise ValidationException(f"Option {section}:{diff} set but not expected.")

            # Check entries we expected but are not there
            for key, key_type in keys.items():
                if not ini_parser.has_option(section, key):
                    raise ValidationException(f"Option {section}:{key} is missing.")
                value = ini_parser.get(section, key)
                if not isinstance(value, key_type):
                    raise ValidationException(f"Option {section}:{key} is not a {key_type}.")

        # List the files, their md5sum, and the complete md5sum
        files = {}
        md5sum = b"\x00" * 16
        for key in self.INI_VALIDATION["files"]:
            filename = ini_parser.get("files", key)
            if filename:
                if not ini_parser.has_option("md5s", filename):
                    raise ValidationException(f"Option md5s:{filename} is missing.")
                if "names" in self.INI_VALIDATION and not ini_parser.has_option("names", filename):
                    raise ValidationException(f"Option names:{filename} is missing.")

                files[filename] = bytes.fromhex(ini_parser.get("md5s", filename))
                # The md5sum of the base-set is the xor of all the individual md5s
                md5sum = bytes([a ^ b for a, b in zip(md5sum, files[filename])])

        # Check not more entries are in md5s section than expected
        for diff in set(files) - set(ini_parser.options("md5s")):
            raise ValidationException(f"Option md5s:{diff} set but not expected.")

        if "names" in self.INI_VALIDATION:
            # Check not more entries are in names section than expected
            for diff in set(files) - set(ini_parser.options("names")):
                raise ValidationException(f"Option names:{diff} set but not expected.")

        self.unique_id = ini_parser.get("metadata", "shortname").encode()
        self.version = ini_parser.get("metadata", "version")
        self.description = ini_parser.get("metadata", "description")
        self.files = files
        self.md5sum = md5sum
