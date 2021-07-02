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
_github_private_key = None
_github_url = None


class Index(LocalIndex):
    def __init__(self):
        # We need to write the private key to disk: GitPython can only use
        # SSH-keys that are written on disk.
        if _github_private_key:
            self._github_private_key_file = tempfile.NamedTemporaryFile()
            self._github_private_key_file.write(_github_private_key)
            self._github_private_key_file.flush()

            self._ssh_command = f"ssh -i {self._github_private_key_file.name}"
        else:
            self._ssh_command = None

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

        # Checkout the latest default branch, removing and commits/file
        # changes local might have.
        with self._git.git.custom_environment(GIT_SSH_COMMAND=self._ssh_command):
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

        if not self._ssh_command:
            log.error("No GitHub private key supplied; cannot push to GitHub.")
            return

        with self._git.git.custom_environment(GIT_SSH_COMMAND=self._ssh_command):
            self._git.remotes.origin.push()


@click_helper.extend
@click.option(
    "--index-github-url",
    help="Repository URL on GitHub; needs to be SSH if you want to be able to write. (index=github only)",
    default="git@github.com:OpenTTD/BaNaNaS.git",
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
    "--index-github-private-key",
    help="Base64-encoded private key to access GitHub."
    "Always use this via an environment variable!"
    "(index=github only)",
)
def click_index_github(index_github_url, index_github_branch, index_github_private_key):
    global _github_url, _github_branch, _github_private_key

    _github_url = index_github_url
    _github_branch = index_github_branch
    if index_github_private_key:
        _github_private_key = base64.b64decode(index_github_private_key)
