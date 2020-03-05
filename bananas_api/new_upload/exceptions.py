class ValidationException(Exception):
    pass


class InvalidUtf8Exception(ValidationException):
    def __init__(self):
        super().__init__("File contains invalid UTF-8 characters; did you really save it as an UTF-8 file?")


class UnknownFileException(ValidationException):
    def __init__(self):
        super().__init__("Could not recognise this file; possibly the extension is wrong?")


class MultipleContentTypeException(ValidationException):
    def __init__(self):
        super().__init__(
            "More than one Content Type was detected, where only one was expected. For example, you are uploading both"
            " a NewGRF and a Scenario in the same package. This is not possible."
        )


class MultipleSameContentTypeException(ValidationException):
    def __init__(self, package_type):
        super().__init__(f"More than one {package_type.value} files was detected, where only one was expected.")


class NoContentTypeException(ValidationException):
    def __init__(self):
        super().__init__("Expecting at least a single file defining the Content Type.")


class CountExactContentTypeException(ValidationException):
    def __init__(self, package_type, count, count_exact):
        super().__init__(f"Expected exact {count_exact} {package_type.value} file(s), but {count} were found.")


class CountMinContentTypeException(ValidationException):
    def __init__(self, package_type, count, count_min):
        super().__init__(f"Expected at least {count_min} {package_type.value} file(s), but {count} were found.")


class UniqueIdNotFourCharactersException(ValidationException):
    def __init__(self):
        super().__init__("Unique ID should be exactly four character.")


class Md5sumOfSubfileDoesntMatchException(ValidationException):
    def __init__(self, base_filename):
        super().__init__(f"The md5sum doesn't match the one mentioned in {base_filename}.")


class BaseSetMentionsFileThatIsNotThereException(ValidationException):
    def __init__(self, filenames):
        super().__init__(f"These files are mentioned but not found: {filenames}.")


class BaseSetDoesntMentionFileException(ValidationException):
    def __init__(self, base_filename):
        super().__init__(f"{base_filename} is not mentioning this file.")


class Utf8FileWithoutBomException(ValidationException):
    def __init__(self):
        super().__init__(
            "File contains UTF-8 characters but doesn't contain UTF-8 BOM. "
            "OpenTTD won't load this file correctly. "
            "Please save the file with 'UTF-8 BOM' encoding."
        )
