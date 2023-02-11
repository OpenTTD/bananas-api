import glob
import yaml

from .newgrf import load_newgrf

from ..helpers.enums import Availability
from ..index.common_disk import Index
from ..new_upload.classifiers.newgrf import classify_newgrf
from ..new_upload.session_validation import validate_packet_size


CLASSIFICATION_TO_FUNCTION = {
    "newgrf": (load_newgrf, classify_newgrf),
}


def reclassify_and_update_metadata(index_folder, storage_folder, category, unique_id, version):
    data = Index(index_folder).read_content_version(f"{category}/{unique_id}", version, load_as_object=True)

    # Load the global data to find things like the name.
    with open(f"{index_folder}/{category}/{unique_id}/global.yaml") as f:
        global_data = yaml.safe_load(f.read())

    name = data.get("name", global_data.get("name", "Unknown"))

    # Prepare a result object, with most things filled in already.
    result = {
        "unique_id": unique_id,
        "version": version,
        "md5sum_partial": data["md5sum_partial"],
        "is_available": data["availability"] == Availability.NEW_GAMES,
        "name": name,
        "error": False,
        "message": "",
        "classification": {},
    }

    # Find the file in the local storage.
    files = glob.glob(f"{storage_folder}/{category}/{unique_id}/{data['md5sum_partial']}*.tar.gz")
    if len(files) == 0:
        result["error"] = True
        result["message"] = "no matching files in local-storage"
        return result
    if len(files) > 1:
        result["error"] = True
        result["message"] = "multiple matching files in local-storage"
        return result

    load_func, classify_func = CLASSIFICATION_TO_FUNCTION[category]

    try:
        obj = load_func(files[0])
    except Exception as e:
        result["error"] = True
        result["message"] = f"error while loading file: {e}"
        return result

    classification = classify_func(obj)
    result["classification"] = classification

    if classification:
        data["classification"] = classification
    elif "classification" in data:
        del data["classification"]

    # In the old days, we allowed the user to "classify" their content.
    # This was a bit of a failure, as people went crazy with it.
    if "tags" in data:
        del data["tags"]

    Index(index_folder).store_version(f"{category}/{unique_id}", data)

    data["errors"] = []
    validate_packet_size(data, {})
    if data["errors"]:
        result["error"] = True
        result["message"] = "error while validating session: " + ", ".join(data["errors"])

    return result
