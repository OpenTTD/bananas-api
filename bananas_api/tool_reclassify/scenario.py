import tarfile

from ..new_upload.readers.scenario import Scenario


def load_scenario(file):
    scenario = Scenario()
    with tarfile.open(file) as tar:
        for member in tar.getmembers():
            if member.name.lower().endswith(".scn"):
                scenario_member = member
                break
        else:
            raise Exception("no SCN in tarball")

        scenario.read(tar.extractfile(scenario_member))

    return scenario
