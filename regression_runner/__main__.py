import aiohttp
import asyncio
import base64
import click
import coloredlogs
import ctypes
import hashlib
import logging
import os
import secrets
import signal
import sys
import verboselogs
import yaml

from collections.abc import Mapping
from ctypes.util import find_library
from tempfile import TemporaryDirectory
from tusclient.client import TusClient

log = verboselogs.VerboseLogger(__name__)

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

auth_headers = {}
startup_event = asyncio.Event()
session = None
python_proc = None
token = "${TOKEN}"
current_regression = ""


class RegressionFailure(Exception):
    pass


class DefinitionFailure(Exception):
    pass


async def api_call(request_command, url, json=None, data=None, silent=False):
    if request_command == "GET":
        return await session.get(f"http://127.0.0.1:8080{url}", headers=auth_headers, allow_redirects=False)
    if request_command == "POST":
        return await session.post(
            f"http://127.0.0.1:8080{url}", data=data, json=json, headers=auth_headers, allow_redirects=False
        )
    if request_command == "PUT":
        return await session.put(
            f"http://127.0.0.1:8080{url}", data=data, json=json, headers=auth_headers, allow_redirects=False
        )
    if request_command == "DELETE":
        return await session.delete(f"http://127.0.0.1:8080{url}", headers=auth_headers, allow_redirects=False)

    raise DefinitionFailure(f"Unknown request-command {request_command}")


def validate_keys(step, fields):
    for key in step:
        if key not in fields and key != "api":
            raise DefinitionFailure(f"Found key '{key}' in definition, which was not expected")


def match_package_in_list(packages_to_match, packages_to_match_to):
    for package in packages_to_match:
        for check_package in packages_to_match_to:
            for version in check_package["versions"]:
                for field in package.keys():
                    if field not in ("version", "license", "md5sum-partial", "availability"):
                        continue

                    if version.get(field) != package[field]:
                        break
                else:
                    # All fields were identical, so we have a match
                    break
            else:
                raise RegressionFailure(f"Couldn't find package in discover self; package={package}")

            for field in package.keys():
                if field in ("version", "license", "md5sum-partial", "availability"):
                    continue

                if check_package.get(field) != package[field]:
                    break
            else:
                # All fields were identical, so we have a match
                break
        else:
            raise RegressionFailure(f"Couldn't find package in discover self; package={package}")


async def handle_user_login(step):
    validate_keys(step, ["api", "username"])

    code_verifier = secrets.token_hex(32)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")

    # Start the OAuth flow
    result = await api_call(
        "GET",
        f"/user/authorize?"
        f"audience=developer&"
        f"response_type=code&"
        f"client_id=regression&"
        f"redirect_uri=http://localhost:12345/&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256",
    )
    if result.status != 200:
        raise RegressionFailure(f"Couldn't login; status_code={result.status}")

    code = result.headers["Developer-Code"]

    # Set our prefered username
    username = step.get("username", "regression")
    result = await api_call("POST", "/user/developer", data=f"username={username}&code={code}")
    if result.status != 302:
        raise RegressionFailure(f"Couldn't login; status_code={result.status}")

    code = result.headers["Location"].split("=")[1]

    # Finish the OAuth flow
    result = await api_call(
        "POST",
        "/user/token",
        json={
            "code": code,
            "client_id": "regression",
            "code_verifier": code_verifier,
            "redirect_uri": "http://localhost:12345/",
            "grant_type": "authorization_code",
        },
    )
    if result.status != 200:
        raise RegressionFailure(f"Couldn't login; status_code={result.status}")

    data = await result.json()
    auth_headers["Authorization"] = f"Bearer {data['access_token']}"

    log.info(f"Logged in as {username}")


async def handle_user_logout(step):
    validate_keys(step, ["api"])

    result = await api_call("GET", "/user/logout")

    if result.status != 204:
        raise RegressionFailure(f"Couldn't logout; status_code={result.status}")

    del auth_headers["Authorization"]


async def handle_discover_self(step):
    validate_keys(step, ["api", "packages"])

    result = await api_call("GET", "/package/self")

    if result.status != 200:
        raise RegressionFailure(f"Couldn't find package in discover self; status_code={result.status}")

    data = await result.json()
    match_package_in_list(step["packages"], data)
    log.info("Found matching package(s) in discover self")


async def handle_discover_content_type(step):
    validate_keys(step, ["api", "content-type", "packages"])

    result = await api_call("GET", f"/package/{step['content-type']}")

    if result.status != 200:
        raise RegressionFailure(
            f"Couldn't find package in discover {step['content-type']}; status_code={result.status}"
        )

    data = await result.json()
    match_package_in_list(step["packages"], data)
    log.info(f"Found matching package(s) dicover {step['content-type']}")


async def handle_discover_unique_id(step):
    validate_keys(step, ["api", "content-type", "unique-id", "packages"])

    result = await api_call("GET", f"/package/{step['content-type']}/{step['unique-id']}")

    if result.status != 200:
        raise RegressionFailure(
            f"Couldn't find package in discover {step['content-type']}/{step['unique-id']}; status_code={result.status}"
        )

    data = await result.json()
    match_package_in_list(step["packages"], [data])
    log.info(f"Found matching package(s) dicover {step['content-type']}/{step['unique-id']}")


async def handle_new_start(step):
    global token

    validate_keys(step, ["api"])

    result = await api_call("POST", "/new-package", json={}, silent=True)

    if result.status != 200:
        raise RegressionFailure(f"Couldn't create new package; status_code={result.status}")

    data = await result.json()
    token = data["upload-token"]
    log.info("Started new session")


async def handle_new_update(step):
    fields = ["version", "name", "description", "license", "url", "tags", "dependencies", "compatibility"]
    validate_keys(step, fields + ["api", "error"])

    payload = {}
    for field in fields:
        if field in step:
            payload[field] = step[field]

    result = await api_call("PUT", f"/new-package/{token}", json=payload)

    if result.status not in (204, 400):
        raise RegressionFailure(f"Couldn't update package info; status_code={result.status}")

    if result.status == 400:
        data = await result.json()

        if "error" in step:
            for key, value in step["error"].items():
                if "." in key:
                    key, _, subkey = key.partition(".")
                else:
                    subkey = None

                if key not in data["errors"]:
                    raise RegressionFailure(f"Expected error during info update not triggered: {key}:{value}")

                if isinstance(data["errors"][key], Mapping):
                    if subkey:
                        if not any(subkey in a and value in a[subkey] for a in data["errors"][key].values()):
                            raise RegressionFailure(
                                f"Expected error during info update not triggered: {key}.{subkey}:{value}"
                            )
                    else:
                        if not any(value in a for a in data["errors"][key].values()):
                            raise RegressionFailure(f"Expected error during info update not triggered: {key}:{value}")
                else:
                    if value not in data["errors"][key]:
                        raise RegressionFailure(f"Expected error during info update not triggered: {key}:{value}")
            log.info("Found expected error during info update")
            return
        else:
            raise RegressionFailure(f"Tried to info update, but there were errors: {data['errors']}")
    elif "error" in step:
        raise RegressionFailure(f"Expected error during info update not triggered: {step['error']}")

    log.info(f"Package info updated with {payload}")


async def handle_new_info(step):
    fields = [
        "version",
        "name",
        "description",
        "url",
        "tags",
        "license",
        "md5sum-partial",
        "content-type",
        "unique-id",
        "dependencies",
        "compatibility",
        "error",
    ]
    validate_keys(step, fields + ["api"])

    result = await api_call("GET", f"/new-package/{token}")

    if result.status != 200:
        raise RegressionFailure(f"Couldn't get package info; status_code={result.status}")

    data = await result.json()

    for field in fields:
        if field not in step:
            continue

        if field == "error":
            dfield = f"{field}s"
            if not step[field]:
                if data[dfield]:
                    raise RegressionFailure(
                        f"Expeced entry '{dfield}' to be empty, but it is not; found: '{data[dfield]}'"
                    )
            elif step[field] not in data[dfield]:
                raise RegressionFailure(
                    f"Entry in '{dfield}' is not there; found: '{data[dfield]}', expected at least '{step[field]}'"
                )
        elif field not in data:
            raise RegressionFailure(f"Field '{field}' is not set; expected '{step[field]}''")
        elif data[field] != step[field]:
            raise RegressionFailure(f"Field '{field}' is different; found: '{data[field]}', expected '{step[field]}'")

    log.info("Package info is as expected")


async def handle_new_publish(step):
    validate_keys(step, ["api", "error"])

    result = await api_call("POST", f"/new-package/{token}/publish", json={})

    if result.status not in (201, 400):
        raise RegressionFailure(f"Couldn't publish package; status_code={result.status}")

    data = await result.json()

    if "error" in step:
        if not data["errors"]:
            raise RegressionFailure("Expected error during publish, but none found")
        if step["error"] not in data["errors"]:
            raise RegressionFailure(f"Expected error during publish not triggered: {step['error']}")
        log.info("Found expected error during publishing")
        return

    if data["errors"]:
        raise RegressionFailure(f"Tried to publish, but there were errors: {data['errors']}")
    log.info("Published")


async def handle_new_delete_file(step):
    validate_keys(step, ["filename", "uuid"])

    if "uuid" in step:
        result = await api_call("DELETE", f"/new-package/{token}/{step['uuid']}")

        if result.status != 404:
            raise RegressionFailure("Could delete file, but that should be impossible")

        log.info("Failed to remove file (expected)")
        return

    result = await api_call("GET", f"/new-package/{token}")

    if result.status != 200:
        raise RegressionFailure(f"Couldn't get package info; status_code={result.status}")

    data = await result.json()

    for file_info in data["files"]:
        if file_info["filename"] == step["filename"]:
            result = await api_call("DELETE", f"/new-package/{token}/{file_info['uuid']}")

            if result.status != 204:
                raise RegressionFailure(f"Couldn't delete file; status_code={result.status}")

            log.info(f"File with name {step['filename']} deleted")
            break
    else:
        raise RegressionFailure(f"No filename {step['filename']} found to delete")


api_mapping = {
    "user/login": handle_user_login,
    "user/loguot": handle_user_logout,
    "discover/self": handle_discover_self,
    "discover/content-type": handle_discover_content_type,
    "discover/unique-id": handle_discover_unique_id,
    "new-package/start": handle_new_start,
    "new-package/update": handle_new_update,
    "new-package/info": handle_new_info,
    "new-package/publish": handle_new_publish,
    "new-package/delete-file": handle_new_delete_file,
}


async def handle_api(step):
    func = api_mapping.get(step["api"])
    if not func:
        raise DefinitionFailure(f"Unknown API {step['api']}")

    await func(step)


async def handle_file_upload(step):
    validate_keys(step, ["file-upload", "name"])

    filename = step["file-upload"]
    fullpath = "/".join(current_regression.split("/")[:-1])
    fullpath = f"{fullpath}/{filename}"

    if "name" in step:
        filename = step["name"]

    tus = TusClient("http://127.0.0.1:1080/new-package/tus/")
    try:
        uploader = tus.uploader(
            fullpath, chunk_size=5 * 1024 * 1024, metadata={"filename": filename, "upload-token": token}
        )
    except Exception:
        raise RegressionFailure(f"Couldn't upload file '{filename}'")
    uploader.upload()


async def set_death_signal():
    PR_SET_PDEATHSIG = 1

    libc = ctypes.CDLL(find_library("c"))
    libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0)


async def _run_api(use_coverage):
    global python_proc

    os.environ["PYTHONPATH"] = os.getcwd()
    os.environ["PYTHONUNBUFFERED"] = "1"

    with TemporaryDirectory(prefix="ottd-api") as folder:
        os.chdir(folder)

        if use_coverage:
            command = ["coverage", "run", "--source", "bananas_api"]
        else:
            command = ["python"]

        command.extend(
            [
                "-m",
                "bananas_api",
                "--web-port",
                "8080",
                "--storage",
                "local",
                "--index",
                "local",
                "--user",
                "developer",
                "--commit-graceperiod",
                "1",
                "--cleanup-graceperiod",
                "5",
                "--client-file",
                os.environ["PYTHONPATH"] + "/regression_runner/clients.yaml",
            ]
        )
        python_proc = await asyncio.create_subprocess_exec(
            command[0],
            *command[1:],
            stdout=asyncio.subprocess.PIPE,
            preexec_fn=set_death_signal,
        )
        os.chdir(os.environ["PYTHONPATH"])

        await python_proc.stdout.readline()
        startup_event.set()
        await python_proc.wait()


step_mapping = {
    "api": handle_api,
    "file-upload": handle_file_upload,
}


async def _handle_file(data):
    if "steps" not in data:
        raise DefinitionFailure("Invalid regression file; no 'steps' defined.")

    for step in data["steps"]:
        for key in step_mapping:
            if key in step:
                func = step_mapping[key]
                break
        else:
            raise DefinitionFailure(f"Unknown step: {step}")

        await func(step)

    if "Authorization" in auth_headers:
        await handle_user_logout({})


async def _handle_files(filenames):
    global current_regression, session

    await startup_event.wait()
    session = aiohttp.ClientSession()

    failed = False

    for filename in filenames:
        current_regression = filename

        try:
            with open(filename, "r") as f:
                data = yaml.safe_load(f)

            await _handle_file(data)
            log.success("Regression test passed")
        except RegressionFailure as e:
            log.critical(e.args[0])
            failed = True
        except Exception:
            log.exception("Internal regression error")
            return True

    return failed


class RegressionFilter(logging.Filter):
    @classmethod
    def install(cls, handler):
        handler.addFilter(cls())

    def filter(self, record):
        record.regression = "/".join(current_regression.split("/")[1:])
        return 1


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("regression-file", type=click.Path(exists=True, dir_okay=False), nargs=-1)
@click.option("--coverage", help="Run subprocess via coverage", is_flag=True)
def main(regression_file, coverage):
    max_len = 0
    for filename in regression_file:
        cur_len = len("/".join(filename.split("/")[1:]))
        if cur_len > max_len:
            max_len = cur_len

    coloredlogs.install(
        fmt="%(asctime)s [%(regression)-" + str(max_len) + "s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    for handler in logging.getLogger().handlers:
        handler.addFilter(RegressionFilter())

    loop = asyncio.get_event_loop()
    loop.create_task(_run_api(coverage))
    failed = loop.run_until_complete(_handle_files(regression_file))
    python_proc.terminate()

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
