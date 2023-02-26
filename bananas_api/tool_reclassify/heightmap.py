import tarfile

from ..new_upload.readers.heightmap import Heightmap


def load_heightmap(file):
    heightmap = Heightmap()
    with tarfile.open(file) as tar:
        for member in tar.getmembers():
            if member.name.lower().endswith(".png"):
                heightmap_member = member
                break
        else:
            raise Exception("no PNG in tarball")

        heightmap.read(tar.extractfile(heightmap_member))

    return heightmap
