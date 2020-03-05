import logging
import os
import yaml

from collections import OrderedDict

from ..helpers.api_schema import (
    Authors,
    Global,
    Package,
    set_dependency_check,
    VersionMinimized,
)
from ..helpers.content_storage import (
    add_to_blacklist,
    clear_indexed_packages,
    get_highest_scenario_heightmap_id,
    get_indexed_count,
    index_package,
    set_if_higher_scenario_heightmap_id,
)
from ..helpers.enums import ContentType

log = logging.getLogger(__name__)


class key_string(str):
    pass


class date_string(str):
    pass


def string_presenter(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')


# Patch YAML to represent our data correctly
yaml.add_representer(OrderedDict, lambda dumper, data: dumper.represent_mapping("tag:yaml.org,2002:map", data.items()))
yaml.add_representer(key_string, lambda dumper, data: dumper.represent_scalar("tag:yaml.org,2002:str", data, style=""))
yaml.add_representer(date_string, lambda dumper, data: dumper.represent_scalar("tag:yaml.org,2002:timestamp", data))
yaml.add_representer(str, string_presenter)


def yaml_dump(data, recursive=False):
    # Bit of trickery to make easier to read (for human) YAML files.
    # We replace all keys of all dicts with key_string(), so we can make sure
    # all values are quoted, where all keys are not.

    result = OrderedDict()
    for key, value in data.items():
        if isinstance(value, OrderedDict):
            value = yaml_dump(value, recursive=True)

        if isinstance(value, list):
            new_value = []
            for entry in value:
                if isinstance(entry, OrderedDict):
                    entry = yaml_dump(entry, recursive=True)
                new_value.append(entry)
            value = new_value

        result[key_string(key)] = value

    if recursive:
        return result

    return yaml.dump(result, width=float("inf"), allow_unicode=True)


class Index:
    def __init__(self, folder):
        self.folder = folder
        self.files = []
        self.changes = []

    def _read_content_entry(self, content_type, folder_name, unique_id):
        folder_name = f"{folder_name}/{unique_id}"

        with open(f"{folder_name}/global.yaml") as f:
            package_data = yaml.safe_load(f.read())

        if package_data.get("blacklisted"):
            return None

        package_data["authors"] = []
        with open(f"{folder_name}/authors.yaml") as f:
            authors_data = yaml.safe_load(f.read())

            for author_data in authors_data.get("authors", []):
                package_data["authors"].append(author_data)

        package_data["versions"] = []
        for version in os.listdir(f"{folder_name}/versions"):
            with open(f"{folder_name}/versions/{version}") as f:
                version_data = yaml.safe_load(f.read())

                # YAML converts this in a datetime() for us, and marshmallow
                # expects a string. So output it as an ISO-8601 again.
                version_data["upload-date"] = version_data["upload-date"].isoformat()

                # Convert all the content-types to ContentType
                for dep in version_data.get("dependencies", []):
                    dep_content_type = ContentType(dep["content-type"])
                    dep["content-type"] = dep_content_type.value

                package_data["versions"].append(version_data)

        package_data["content-type"] = content_type.value
        package_data["unique-id"] = unique_id

        return Package().load(package_data)

    def reload(self):
        clear_indexed_packages()
        self.load_all()

    def load_all(self):
        # Because we are loaded the content, there is no way to already do
        # dependency validation. So for now, disable it. After we loaded
        # everything, we will give it another pass to validate dependencies.
        set_dependency_check(False)

        version_dep_check = []
        for content_type in ContentType:
            folder_name = f"{self.folder}/{content_type.value}"

            if not os.path.isdir(folder_name):
                continue

            for unique_id in os.listdir(folder_name):
                try:
                    package = self._read_content_entry(content_type, folder_name, unique_id)
                except Exception:
                    log.exception(f"Failed to load entry {folder_name}/{unique_id}. Skipping.")
                    continue

                # Return of None means package is blacklisted
                if package is None:
                    add_to_blacklist(content_type, unique_id)
                    continue

                index_package(package)

                for version in package["versions"]:
                    version_dep_check.append(version)

                # Scenarios and heightmap share their index in the OpenTTD client.
                # Their unique-id is also assigned by us (and not the user as with
                # all the other content). As such, find the highest currently used
                # number, and store that.
                if content_type in (ContentType.SCENARIO, ContentType.HEIGHTMAP):
                    set_if_higher_scenario_heightmap_id(int(unique_id, 16))

            log.info("Loaded %d entries for %s", get_indexed_count(content_type), content_type.value)

        log.info("Highest unique-id used by scenario/heightmap is %d", get_highest_scenario_heightmap_id())

        set_dependency_check(True)

        # Validate all loaded versions, this time with dependency checking on.
        # This to make sure we are in a consistent state.
        for version in version_dep_check:
            errors = VersionMinimized().validate(VersionMinimized().dump(version))
            if errors:
                raise Exception("Failed to load content entries: %r" % errors)

    def store_package(self, package, display_name):
        self.changes.append(f"{package['content_type'].value}/{package['unique_id']} (by {display_name})")
        path = f"{package['content_type'].value}/{package['unique_id']}"

        os.makedirs(f"{self.folder}/{path}/versions", exist_ok=True)

        data = Global().dump(package)
        self.files.append(f"{path}/global.yaml")
        with open(f"{self.folder}/{path}/global.yaml", "w") as fp:
            fp.write(yaml_dump(data))

        data = Authors().dump({"authors": package["authors"]})
        self.files.append(f"{path}/authors.yaml")
        with open(f"{self.folder}/{path}/authors.yaml", "w") as fp:
            fp.write(yaml_dump(data))

        for version in package["versions"]:
            data = VersionMinimized().dump(version)
            data["upload-date"] = date_string(data["upload-date"].replace("+00:00", "Z"))
            upload_date = data["upload-date"].replace("-", "").replace(":", "")

            # Make sure the overwrite fields are at the bottom; this just reads a
            # bit easier.
            data_overwrite = OrderedDict()
            for field in Global().fields:
                if field in data:
                    data_overwrite[field] = data[field]
                    del data[field]

            self.files.append(f"{path}/versions/{upload_date}.yaml")
            with open(f"{self.folder}/{path}/versions/{upload_date}.yaml", "w") as fp:
                fp.write(yaml_dump(data))
                if data_overwrite:
                    fp.write("\n")
                    fp.write(yaml_dump(data_overwrite))
