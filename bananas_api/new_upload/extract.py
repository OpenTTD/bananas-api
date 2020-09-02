import tarfile
import os
import secrets
import zipfile

from .exceptions import ArchiveError

TAR_STORAGE_PATH = "data/tar"


def _find_root_folder(info_list, get_name=None, is_file=None):
    """
    Tar-files are often made of a whole folder. This means that we would
    prefix all files with that folder name, which in 99% of the cases
    won't be the expected outcome. So first do a scan, to see if there
    are any files or more than one directory in the root folder. If not,
    skip the root-folder while extracting.

    To keep things more the same, do this also for any other format.
    """

    root_folder = None

    for info in info_list:
        if not is_file(info):
            continue

        if root_folder is None:
            root_folder = get_name(info).split("/")[0]

        if not get_name(info).startswith(f"{root_folder}/"):
            root_folder = None
            break

    return root_folder


def _extract_files(info_list, root_folder, extractor, extractor_kwargs, get_name=None, set_name=None, is_file=None):
    files = []

    for info in info_list:
        if not is_file(info):
            continue

        # Chance on collision is really low, but would be really annoying. So
        # simply protect against it by looking for an unused UUID.
        uuid = secrets.token_hex(16)
        while os.path.isfile(os.path.join(TAR_STORAGE_PATH, uuid)):
            uuid = secrets.token_hex(16)

        internal_filename = os.path.join(TAR_STORAGE_PATH, uuid)

        new_file = {
            "uuid": uuid,
            "filename": get_name(info),
            "internal_filename": internal_filename,
            "errors": [],
        }

        # Remove the root-folder from the filename if needed.
        if root_folder:
            new_file["filename"] = new_file["filename"][len(root_folder) + 1 :]

        # Change the filename and extract to it; this flattens everything,
        # which means we won't have empty folders to deal with.
        set_name(info, uuid)
        extractor.extract(info, TAR_STORAGE_PATH, **extractor_kwargs)

        new_file["filesize"] = os.stat(internal_filename).st_size
        files.append(new_file)

    return files


def extract_tarball(file_info):
    def set_tar_name(info, value):
        info.name = value

    try:
        with tarfile.open(file_info["internal_filename"]) as tar:
            root_folder = _find_root_folder(
                tar,
                get_name=lambda info: info.name,
                is_file=lambda info: info.isfile(),
            )

            files = _extract_files(
                tar,
                root_folder,
                extractor=tar,
                extractor_kwargs={"set_attrs": False},
                get_name=lambda info: info.name,
                set_name=set_tar_name,
                is_file=lambda info: info.isfile(),
            )
    except tarfile.ReadError:
        raise ArchiveError

    return files


def extract_zip(file_info):
    def set_zip_name(info, value):
        info.filename = value

    try:
        with zipfile.ZipFile(file_info["internal_filename"]) as zip:
            root_folder = _find_root_folder(
                zip.infolist(),
                get_name=lambda info: info.filename,
                is_file=lambda info: not info.is_dir(),
            )

            files = _extract_files(
                zip.infolist(),
                root_folder,
                extractor=zip,
                extractor_kwargs={},
                get_name=lambda info: info.filename,
                set_name=set_zip_name,
                is_file=lambda info: not info.is_dir(),
            )
    except zipfile.BadZipFile:
        raise ArchiveError

    return files
