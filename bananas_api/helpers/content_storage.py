from collections import defaultdict


# A bit hackish, but create a local storage to store information about
# packages we know. This allows easier wrappers around these variables
# for other parts of the code to access.
class LocalStorage:
    highest_scenario_heightmap_id = 0
    by_content_type = defaultdict(dict)
    by_author = defaultdict(lambda: defaultdict(list))
    by_version = defaultdict(lambda: defaultdict(dict))
    blacklist = defaultdict(set)

    def clear(self):
        # Never reset highest_scenario_heightmap_id
        self.by_content_type.clear()
        self.by_author.clear()
        self.by_version.clear()
        self.blacklist.clear()


local_storage = LocalStorage()


def add_to_blacklist(content_type, unique_id):
    local_storage.blacklist[content_type].add(unique_id)


def get_highest_scenario_heightmap_id():
    return local_storage.highest_scenario_heightmap_id


def set_if_higher_scenario_heightmap_id(id):
    if id > local_storage.highest_scenario_heightmap_id:
        local_storage.highest_scenario_heightmap_id = id


def increase_scenario_heightmap_id():
    local_storage.highest_scenario_heightmap_id += 1


def index_package(package, index_versions=True):
    local_storage.by_content_type[package["content_type"]][package["unique_id"]] = package

    if index_versions:
        for version in package["versions"]:
            local_storage.by_version[package["content_type"]][package["unique_id"]][version["upload_date"]] = version

    for author in package["authors"]:
        for key, value in author.items():
            if key == "display_name":
                continue

            local_storage.by_author[key][value].append(package)


def index_version(content_type, unique_id, version):
    local_storage.by_version[content_type][unique_id][version["upload_date"]] = version


def get_indexed_count(content_type):
    return len(local_storage.by_content_type[content_type])


def get_indexed_package(content_type, unique_id):
    return local_storage.by_content_type[content_type].get(unique_id)


def get_indexed_version(content_type, unique_id, upload_date):
    return local_storage.by_version[content_type].get(unique_id, {}).get(upload_date)


def get_indexed_packages(content_type=None, user=None):
    if content_type:
        return local_storage.by_content_type[content_type].values()
    if user:
        return local_storage.by_author[user.method].get(user.id, [])


def clear_indexed_packages():
    local_storage.clear()
