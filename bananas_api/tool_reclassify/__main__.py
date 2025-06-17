import click
import glob

from concurrent.futures import ProcessPoolExecutor
from openttd_helpers import click_helper

from .reclassify import reclassify_and_update_metadata
from ..helpers.api_schema import Classification, set_dependency_check

TOTAL_ENTRIES = 0
TOTAL_FINISHED = 0


def update_progress(unique_id, version, md5sum_partial, name, error, message, classification, is_available):
    global TOTAL_FINISHED
    TOTAL_FINISHED += 1

    if error:
        print(f"[{TOTAL_FINISHED} / {TOTAL_ENTRIES} - {unique_id}:{md5sum_partial} - {name}] ERROR: {message}")
    elif is_available:
        print(
            f"[{TOTAL_FINISHED} / {TOTAL_ENTRIES} - {unique_id}:{md5sum_partial} - {name}] "
            + ",".join(f"{k}={v}" for k, v in Classification().dump(classification).items())
        )


@click_helper.command()
@click.option(
    "--index-local-folder",
    help="Folder to use for index storage.",
    type=click.Path(dir_okay=True, file_okay=False),
    default="BaNaNaS",
    show_default=True,
)
@click.option(
    "--storage-local-folder",
    help="Folder to use for storage.",
    type=click.Path(dir_okay=True, file_okay=False),
    default="local_storage",
    show_default=True,
)
@click.argument("category", type=click.Choice(["heightmap", "newgrf", "scenario"]))
@click.argument("unique_id", type=str, required=False)
def main(index_local_folder, storage_local_folder, category, unique_id):
    global TOTAL_ENTRIES

    # Don't do any dependency checking while running this tool.
    set_dependency_check(False)

    # Create a list of entries we need to classify.
    entries = []
    if unique_id is None:
        for unique_id in sorted(glob.glob(f"{index_local_folder}/{category}/*")):
            unique_id = unique_id.split("/")[-1]

            for version in sorted(glob.glob(f"{index_local_folder}/{category}/{unique_id}/versions/*.yaml")):
                version = version.split("/")[-1].split(".")[0]

                entries.append((unique_id, version))
    else:
        for version in sorted(glob.glob(f"{index_local_folder}/{category}/{unique_id}/versions/*.yaml")):
            version = version.split("/")[-1].split(".")[0]

            entries.append((unique_id, version))

    TOTAL_ENTRIES = len(entries)

    # Send all tasks to the executor, which means the classifications will be done in parallel.
    executor = ProcessPoolExecutor()
    for unique_id, version in entries:
        job = executor.submit(
            reclassify_and_update_metadata, index_local_folder, storage_local_folder, category, unique_id, version
        )
        job.add_done_callback(lambda x: update_progress(**x.result()))


if __name__ == "__main__":
    main()
