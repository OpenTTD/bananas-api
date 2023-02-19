import logging
import re

from collections import defaultdict

from ..helpers.enums import (
    ContentType,
    PackageType,
)
from .classifiers.newgrf import classify_newgrf
from .exceptions import (
    BaseSetDoesntMentionFileException,
    BaseSetMentionsFileThatIsNotThereException,
    CountExactContentTypeException,
    CountMinContentTypeException,
    InvalidUtf8Exception,
    NoContentTypeException,
    Md5sumOfSubfileDoesntMatchException,
    MultipleContentTypeException,
    MultipleSameContentTypeException,
    UniqueIdNotFourCharactersException,
    UnknownFileException,
    ValidationException,
)
from .readers.base_graphics import BaseGraphics
from .readers.base_music import BaseMusic
from .readers.base_sounds import BaseSounds
from .readers.cat import Cat
from .readers.heightmap import Heightmap
from .readers.midi import Midi
from .readers.newgrf import NewGRF
from .readers.scenario import Scenario
from .readers.script import (
    EntryScript,
    Script,
)

TARBALL_EXTENSIONS = (".tar", ".tar.gz", ".tgz")
ZIPFILE_EXTENSIONS = (".zip",)

log = logging.getLogger(__name__)

READERS = {
    "grf": NewGRF,
    "scn": Scenario,
    "png": Heightmap,
    "nut": Script,
    "obg": BaseGraphics,
    "obm": BaseMusic,
    "obs": BaseSounds,
    "cat": Cat,
    "mid": Midi,
    "gm": Midi,
}

CLASSIFIERS = {
    PackageType.NEWGRF: classify_newgrf,
}

PACKAGE_TYPE_PAIRS = {
    PackageType.BASE_GRAPHICS: {
        "secondary": PackageType.NEWGRF,
        "count_exact": 6,
    },
    PackageType.BASE_MUSIC: {
        "secondary": PackageType.MUSIC_FILES,
        "count_min": 1,
    },
    PackageType.BASE_SOUNDS: {
        "secondary": PackageType.SOUND_FILES,
        "count_exact": 1,
    },
    PackageType.AI: {
        "secondary": PackageType.SCRIPT_MAIN_FILE,
        "count_exact": 1,
    },
    PackageType.AI_LIBRARY: {
        "secondary": PackageType.SCRIPT_MAIN_FILE,
        "count_exact": 1,
    },
    PackageType.GAME_SCRIPT: {
        "secondary": PackageType.SCRIPT_MAIN_FILE,
        "count_exact": 1,
    },
    PackageType.GAME_SCRIPT_LIBRARY: {
        "secondary": PackageType.SCRIPT_MAIN_FILE,
        "count_exact": 1,
    },
    PackageType.HEIGHTMAP: {},
    PackageType.NEWGRF: {},
    PackageType.SCENARIO: {},
}

# readme.txt and changelog.txt can have translations. This can be with the
# first part of the ISO code, or with the full. For example:
# readme.txt, readme_nl.txt, readme_nl_NL.txt
# All other variantions are not valid.
txt_regexp = re.compile(r"(readme|changelog)(_[a-z]{2}(_[A-Z]{2})?)?\.txt$")


def _validate_textfile_encoding(fp):
    try:
        fp.read().decode()
    except UnicodeDecodeError:
        raise InvalidUtf8Exception


def _read_object(filename, fp):
    lfilename = filename.lower()
    if lfilename.endswith(".txt"):
        if filename == "license.txt":
            _validate_textfile_encoding(fp)
            return None
        elif txt_regexp.match(filename):
            _validate_textfile_encoding(fp)
            return None
        elif filename.startswith("lang/"):
            _validate_textfile_encoding(fp)
            return None
        else:
            raise UnknownFileException
    elif filename in ("info.nut", "library.nut"):
        reader = EntryScript
    else:
        reader = READERS.get(lfilename.split(".")[-1])

        if not reader:
            raise UnknownFileException

    obj = reader()
    obj.filename = filename
    obj.read(fp)

    if lfilename == "main.nut":
        obj.package_type = PackageType.SCRIPT_MAIN_FILE

    return obj


def _find_content_type(objects):
    package_types = defaultdict(lambda: 0)
    for obj in objects:
        package_types[obj.package_type] += 1

    if len(package_types) == 0:
        raise NoContentTypeException

    content_type = None
    for primary_package_type, data in PACKAGE_TYPE_PAIRS.items():
        if "secondary" in data:
            package_type = _find_package_type_dual(
                package_types,
                primary_package_type,
                data["secondary"],
                count_exact=data.get("count_exact"),
                count_min=data.get("count_min"),
            )
        elif primary_package_type in package_types:
            if len(package_types) > 1:
                raise MultipleContentTypeException
            if package_types[primary_package_type] > 1:
                raise MultipleSameContentTypeException(primary_package_type)
            package_type = list(package_types.keys())[0]
        else:
            package_type = None

        if package_type:
            content_type = getattr(ContentType, package_type.name)
            break

    if not content_type:
        raise NoContentTypeException

    return content_type


def _find_package_type_dual(
    package_types, primary_package_type, secondary_package_type, count_exact=None, count_min=None
):
    if primary_package_type not in package_types:
        return None

    if package_types[primary_package_type] > 1:
        raise MultipleSameContentTypeException(primary_package_type)

    count = package_types[secondary_package_type]

    if count_exact and count != count_exact:
        raise CountExactContentTypeException(secondary_package_type, count, count_exact)
    if count_min and count < count_min:
        raise CountMinContentTypeException(secondary_package_type, count, count_min)

    if secondary_package_type == PackageType.SCRIPT_MAIN_FILE and PackageType.SCRIPT_FILES in package_types:
        if len(package_types) != 3:
            raise MultipleContentTypeException
    elif len(package_types) != 2:
        raise MultipleContentTypeException
    return primary_package_type


def validate_files(files):
    errors = False
    objects = []
    for file_info in files:
        # Archives that already have an error failed to extract; no need to do
        # any further validation on them. Archives without an error is most
        # likely a user uploading an archive in an archive. Show him an error
        # that the archive extension is not supported. They should be able to
        # figure it out from there.
        if file_info["filename"].endswith(TARBALL_EXTENSIONS + ZIPFILE_EXTENSIONS) and len(file_info["errors"]) > 0:
            continue

        file_info["errors"] = []

        with open(file_info["internal_filename"], "rb") as fp:
            try:
                obj = _read_object(file_info["filename"], fp)
            except ValidationException as e:
                file_info["errors"].append(e.args[0])
                errors = True
                continue

        if obj:
            file_info["package_type"] = obj.package_type
            obj.file_info = file_info
            obj.classification = CLASSIFIERS.get(obj.package_type, lambda obj: None)(obj)
            objects.append(obj)

    if errors:
        return None

    # Detect the main package
    content_type = _find_content_type(objects)

    # Validate for base-sets that the md5sums of the subfiles are the ones
    # listed in the base-set metadata file.
    if content_type in (ContentType.BASE_GRAPHICS, ContentType.BASE_MUSIC, ContentType.BASE_SOUNDS):
        for obj in objects:
            if obj.package_type.name == content_type.name:
                base_obj = obj
                files_to_check = obj.files.copy()

                break
        else:
            raise Exception("Internal error: found package type but couldn't find object declaring it")

        for obj in objects:
            if obj.filename in files_to_check:
                # Check if md5sums match.
                if files_to_check[obj.filename] != obj.md5sum:
                    obj.file_info["errors"].append(Md5sumOfSubfileDoesntMatchException(base_obj.filename).args[0])
                    errors = True
                del files_to_check[obj.filename]
            elif obj.package_type not in (PackageType.BASE_GRAPHICS, PackageType.BASE_MUSIC, PackageType.BASE_SOUNDS):
                # Mention that this file is not expected.
                obj.file_info["errors"].append(BaseSetDoesntMentionFileException(base_obj.filename).args[0])

        # Check if there wasn't a mention of a file that is not uploaded.
        if len(files_to_check):
            base_obj.file_info["errors"].append(
                BaseSetMentionsFileThatIsNotThereException(", ".join(files_to_check.keys())).args[0]
            )

    if errors:
        return None

    # Collect md5sum, unique_id, and classification of this package
    for obj in objects:
        if obj.package_type.name == content_type.name:
            md5sum = obj.md5sum
            unique_id = getattr(obj, "unique_id", None)
            classification = obj.classification

            if unique_id and len(unique_id) != 4:
                raise UniqueIdNotFourCharactersException

            break
    else:
        raise Exception("Internal error: found package type but couldn't find object declaring it")

    # Script package also have the md5sum of all the .nut files xor'd with the md5sum.
    if content_type in (
        ContentType.AI,
        ContentType.AI_LIBRARY,
        ContentType.GAME_SCRIPT,
        ContentType.GAME_SCRIPT_LIBRARY,
    ):
        for obj in objects:
            if obj.package_type in (PackageType.SCRIPT_FILES, PackageType.SCRIPT_MAIN_FILE):
                md5sum = bytes([a ^ b for a, b in zip(md5sum, obj.md5sum)])

    if unique_id:
        unique_id = unique_id.hex()

    result = {
        "content_type": content_type,
        "unique_id": unique_id,
        "md5sum": md5sum.hex(),
    }

    if classification:
        result["classification"] = classification

    return result
