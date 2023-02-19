import tarfile

from ..new_upload.readers.newgrf import NewGRF


def load_newgrf(file):
    newgrf = NewGRF()
    with tarfile.open(file) as tar:
        for member in tar.getmembers():
            if member.name.lower().endswith(".grf"):
                newgrf_member = member
                break
        else:
            raise Exception("no GRF in tarball")

        newgrf.read(tar.extractfile(newgrf_member))

    return newgrf
