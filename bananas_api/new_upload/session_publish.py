import click
import dateutil.parser
import io
import os
import tarfile

from datetime import (
    datetime,
    timezone,
)
from tempfile import NamedTemporaryFile
from openttd_helpers import click_helper

from ..helpers.api_schema import (
    Package,
    UploadStatus,
    VersionMinimized,
)
from ..helpers.content_save import store_on_disk
from ..helpers.content_storage import (
    get_indexed_package,
    get_highest_scenario_heightmap_id,
    increase_scenario_heightmap_id,
    index_package,
    index_version,
)
from ..helpers.enums import (
    Availability,
    ContentType,
    License,
    PackageType,
)
from ..storage.local import click_storage_local
from ..storage.s3 import click_storage_s3

_storage_instance = None

# Only for certain content-type it makes sense to have a region.
CONTENT_TYPE_WITH_REGION = (
    ContentType.NEWGRF,
    ContentType.HEIGHTMAP,
    ContentType.SCENARIO,
)


def _tar_add_file_from_string(tar, arcname, content):
    content = content.encode()
    stream = io.BytesIO(content)

    info = tarfile.TarInfo(arcname)
    info.size = len(content)

    tar.addfile(info, stream)


def _safe_name(name):
    new_name = ""

    for letter in name:
        if (
            (letter >= "a" and letter <= "z")
            or (letter >= "A" and letter <= "Z")
            or (letter >= "0" and letter <= "9")
            or letter == "."
        ):
            new_name += letter
        elif new_name and new_name[-1] != "_":
            new_name += "_"

    return new_name.strip("._")


def _create_tarball(session, filename, tar_path):
    with tarfile.open(filename, mode="w:gz", format=tarfile.USTAR_FORMAT) as tar:
        # The OpenTTD client's tar extraction implementation demands a root
        # folder at the start of a tar. It only extracts Base Music, so we are
        # only adding it there. As we don't really have a root-folder, we have
        # to make one virtually ourself.
        if session["content_type"] == ContentType.BASE_MUSIC:
            # We use the information of the first file, and convert the node into a
            # directory after. This makes sure things like owner and mtime are set
            # correctly on the folder.
            root_folder = tar.gettarinfo(session["files"][0]["internal_filename"], arcname=tar_path)
            root_folder.mode = 0o755
            root_folder.type = tarfile.DIRTYPE
            root_folder.size = 0

            tar.addfile(root_folder)

        for file_info in sorted(session["files"], key=lambda x: x["filename"]):
            arcname = f"{tar_path}/{file_info['filename']}"
            tar.add(file_info["internal_filename"], arcname=arcname)

        if session["license"] != License.CUSTOM:
            license_file = f"{os.path.dirname(__file__)}/../../licenses/{session['license'].value}.txt"
            tar.add(license_file, arcname=f"{tar_path}/license.txt")

        # Scenarios and heightmaps are missing some meta data on their own
        # so this is added by adding two extra files to the tarball.
        if session["content_type"] in (ContentType.SCENARIO, ContentType.HEIGHTMAP):
            # Find the filename of the scenario / heightmap.
            for file_info in session["files"]:
                if file_info.get("package_type") in (PackageType.SCENARIO, PackageType.HEIGHTMAP):
                    main_filename = file_info["filename"]
                    break
            else:
                raise Exception(
                    "Internal error: content-type is scenario/heightmap,"
                    " but no file found that is a scenario/heightmap."
                )

            # Create a .id file with the decimal unique-id in there.
            arcname = f"{tar_path}/{main_filename}.id"
            _tar_add_file_from_string(tar, arcname, str(int(session["unique_id"], 16)))

            # Create a .title file with the name and version in there.
            arcname = f"{tar_path}/{main_filename}.title"
            _tar_add_file_from_string(tar, arcname, f"{session['name']} ({session['version']})")

    return os.stat(filename).st_size


def create_tarball(session):
    # Scenarios and heightmaps get an unique-id assigned by us.
    if session["content_type"] in (ContentType.SCENARIO, ContentType.HEIGHTMAP):
        increase_scenario_heightmap_id()
        session["unique_id"] = "%08x" % get_highest_scenario_heightmap_id()

    name = session.get("name")
    if not name:
        # If the name is empty, we are an update of an existing package, so
        # use the name of the existing package.
        package = get_indexed_package(session["content_type"], session["unique_id"])
        name = package["name"]

    # Create the tarball and move it into the storage system.
    tempfile_tar = NamedTemporaryFile(dir=".", delete=False, suffix=".tar")
    tar_path = _safe_name(name) + "-" + _safe_name(session["version"])
    try:
        filesize = _create_tarball(session, tempfile_tar.name, tar_path)
        _storage_instance.move_to_storage(
            tempfile_tar.name, session["content_type"], session["unique_id"], session["md5sum"]
        )
    except Exception:
        os.unlink(tempfile_tar.name)
        raise

    session["filesize"] = filesize


def create_package(session):
    # We convert it to isoformat and back to get ride of the microseconds.
    upload_date = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    upload_date = dateutil.parser.isoparse(upload_date)
    session["upload_date"] = upload_date

    # Convert parts of the UploadStatus to a VersionMinimized
    raw_data = UploadStatus().dump(session)
    version_data = {
        "availability": "new-games",
    }
    for field in ("upload-date", "md5sum-partial", "filesize", "license", "version"):
        version_data[field] = raw_data[field]
    if "classification" in raw_data:
        version_data["classification"] = raw_data["classification"]
    for field in ("dependencies", "compatibility"):
        if field in raw_data:
            version_data[field] = raw_data[field]

    package = get_indexed_package(session["content_type"], session["unique_id"])
    if package:
        # Package already exists; update latest version to be "savegame-only"
        # and add this new version. Make sure to run it through the validator,
        # just to make sure we are adding valid entries.

        for version in package["versions"]:
            if version["availability"] == Availability.NEW_GAMES:
                version["availability"] = Availability.SAVEGAMES_ONLY

        for field in ("name", "description", "url"):
            if field in raw_data:
                version_data[field] = raw_data[field]

        if "regions" in raw_data and session["content_type"] in CONTENT_TYPE_WITH_REGION:
            version_data["regions"] = sorted(raw_data["regions"])
    else:
        # This is a new package, so construct it from the ground up. Run it
        # through the validator, just to make sure we are adding valid
        # entries.

        package_data = {
            "content-type": session["content_type"].value,
            "unique-id": session["unique_id"],
            "name": raw_data["name"],
            "authors": [{"display-name": session["user"].display_name, session["user"].method: session["user"].id}],
            "versions": [],
        }

        for field in ("description", "url"):
            if field in raw_data:
                package_data[field] = raw_data[field]

        if "regions" in raw_data and session["content_type"] in CONTENT_TYPE_WITH_REGION:
            package_data["regions"] = sorted(raw_data["regions"])

        package = Package().load(package_data)

        index_package(package, index_versions=False)

    version = VersionMinimized().load(version_data)

    package["versions"].append(version)
    index_version(session["content_type"], session["unique_id"], version)

    store_on_disk(session["user"], package)


@click_helper.extend
@click.option(
    "--storage",
    help="Storage backend to use.",
    type=click.Choice(["local", "s3"], case_sensitive=False),
    required=True,
    callback=click_helper.import_module("bananas_api.storage", "Storage"),
)
@click_storage_local
@click_storage_s3
def click_storage(storage):
    global _storage_instance
    _storage_instance = storage()
