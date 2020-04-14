import click
import os

from ..helpers.click import click_additional_options

_folder = None


class Storage:
    def __init__(self):
        self.folder = _folder

    def move_to_storage(self, filename, content_type, unique_id, md5sum):
        folder = f"{self.folder}/{content_type.value}/{unique_id}"
        new_filename = f"{folder}/{md5sum}.tar.gz"

        os.makedirs(folder, exist_ok=True)
        os.rename(filename, new_filename)


@click_additional_options
@click.option(
    "--storage-local-folder",
    help="Folder to use for storage. (storage=local only)",
    type=click.Path(dir_okay=True, file_okay=False),
    default="local_storage",
    show_default=True,
)
def click_storage_local(storage_local_folder):
    global _folder

    _folder = storage_local_folder
