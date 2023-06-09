import base64
import click
import git
import logging
import tempfile
import os

from openttd_helpers import click_helper

from .local import Index as LocalIndex

log = logging.getLogger(__name__)

_github_branch = None
_github_deploy_key = None
_github_url = None
_github_app_id = None
_github_app_key = None


class Index(LocalIndex):
    def __init__(self):
        self._ssh_command = None
        self._ask_pass = None

        if _github_deploy_key:
            # We need to write the private key to disk: GitPython can only use
            # SSH-keys that are written on disk.
            self._github_deploy_key_file = tempfile.NamedTemporaryFile()
            self._github_deploy_key_file.write(_github_deploy_key)
            self._github_deploy_key_file.flush()

            self._ssh_command = f"ssh -i {self._github_deploy_key_file.name}"
        elif _github_app_id and _github_app_key:
            self._ask_pass = os.path.join(os.path.dirname(__file__), "github-askpass.py")
        else:
            log.info("Neither a GitHub Deploy key nor a GitHub App is provided")
            log.info("Please make sure you have a credential helper configured for this repository.")

        super().__init__()

    def prepare(self):
        super().prepare()

        # Make sure the origin is set correctly
        if "origin" not in self._git.remotes:
            self._git.create_remote("origin", _github_url)
        origin = self._git.remotes.origin
        if origin.url != _github_url:
            origin.set_url(_github_url)

        self._fetch_latest(_github_branch)

    def _remove_empty_folders(self, parent_folder):
        removed = False
        for root, folders, files in os.walk(parent_folder, topdown=False):
            if root.startswith(".git"):
                continue

            if not folders and not files:
                os.rmdir(root)
                removed = True

        return removed

    def _fetch_latest(self, branch):
        log.info("Updating index to latest version from GitHub")

        origin = self._git.remotes.origin

        git_env = {}
        if self._ssh_command:
            git_env["GIT_SSH_COMMAND"] = self._ssh_command
        elif self._ask_pass:
            git_env["GIT_ASKPASS"] = self._ask_pass

        # Checkout the latest default branch, removing and commits/file
        # changes local might have.
        with self._git.git.custom_environment(**git_env):
            try:
                origin.fetch()
            except git.exc.BadName:
                # When the garbage collector kicks in, GitPython gets confused and
                # throws a BadName. The best solution? Just run it again.
                origin.fetch()
        origin.refs[branch].checkout(force=True, B=branch)
        for file_name in self._git.untracked_files:
            os.unlink(f"{self.folder}/{file_name}")

        # We might end up with empty folders, which the rest of the
        # application doesn't really like. So remove them. Keep repeating the
        # function until no folders are removed anymore.
        while self._remove_empty_folders(self.folder):
            pass

    def reload(self):
        self._fetch_latest(_github_branch)
        super().reload()

    def push_changes(self):
        super().push_changes()

        git_env = {}
        if self._ssh_command:
            git_env["GIT_SSH_COMMAND"] = self._ssh_command
        elif self._ask_pass:
            git_env["GIT_ASKPASS"] = self._ask_pass

        with self._git.git.custom_environment(**git_env):
            self._git.remotes.origin.push()


@click_helper.extend
@click.option(
    "--index-github-url",
    help="Repository URL on GitHub; needs to be SSH if you want to be able to write. (index=github only)",
    default="https://github.com/OpenTTD/BaNaNaS",
    show_default=True,
    metavar="URL",
)
@click.option(
    "--index-github-branch",
    help="Branch of the GitHub repository to use.",
    default="main",
    show_default=True,
    metavar="branch",
)
@click.option(
    "--index-github-deploy-key",
    "--index-github-private-key",  # Deprecated; use --index-github-deploy-key instead.
    help="Base64-encoded GitHub Deploy key to access the repository. Use either this or a GitHub App. "
    "Always use this via an environment variable! (index=github only)",
)
@click.option(
    "--index-github-app-id",
    help="GitHub App ID that has write access to the repository. Use either this or a GitHub Deploy Key. "
    "(index=github only)",
)
@click.option(
    "--index-github-app-key",
    help="Base64-encoded GitHub App Private Key. Use either this or a GitHub Deploy Key. "
    "Always use this via an environment variable! (index=github only)",
)
@click.option(
    "--index-github-api-url",
    help="GitHub API URL to use with GitHub App. (index=github only)",
    default="https://api.github.com",
    show_default=True,
    metavar="URL",
)
def click_index_github(
    index_github_url,
    index_github_branch,
    index_github_deploy_key,
    index_github_app_id,
    index_github_app_key,
    index_github_api_url,
):
    global _github_url, _github_branch, _github_deploy_key, _github_app_id, _github_app_key

    _github_url = index_github_url
    _github_branch = index_github_branch

    if index_github_deploy_key:
        _github_deploy_key = base64.b64decode(index_github_deploy_key)
    elif index_github_app_id and index_github_app_key:
        # Make sure we can base64 decode it, but we keep the base64 encoded value.
        base64.b64decode(index_github_app_key)

        _github_app_id = index_github_app_id
        _github_app_key = index_github_app_key

        # Use the environment to pass information to the ask-pass script.
        # This way things like the key are never visible in the process list.
        os.environ["BANANAS_API_GITHUB_ASKPASS_APP_ID"] = _github_app_id
        os.environ["BANANAS_API_GITHUB_ASKPASS_APP_KEY"] = _github_app_key
        os.environ["BANANAS_API_GITHUB_ASKPASS_URL"] = _github_url
        os.environ["BANANAS_API_GITHUB_ASKPASS_API_URL"] = index_github_api_url
