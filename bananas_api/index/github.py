import base64
import click
import logging
import tempfile
import os

from .local import Index as LocalIndex
from ..helpers.click import click_additional_options

log = logging.getLogger(__name__)

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

    def _prepare_git(self):
        super()._prepare_git()

        # Make sure the origin is set correctly
        if "origin" not in self._git.remotes:
            self._git.create_remote("origin", _github_url)
        origin = self._git.remotes.origin
        if origin.url != _github_url:
            origin.set_url(_github_url)

        self._fetch_latest()

    def _fetch_latest(self):
        log.info("Updating index to latest version from GitHub")

        origin = self._git.remotes.origin

        # Checkout the latest master, removing and commits/file changes local
        # might have.
        with self._git.git.custom_environment(GIT_SSH_COMMAND=self._ssh_command):
            origin.fetch()
        origin.refs.master.checkout(force=True, B="master")
        for file_name in self._git.untracked_files:
            os.unlink(f"{self.folder}/{file_name}")

    def reload(self):
        self._fetch_latest()
        super().reload()

    def push_changes(self):
        super().push_changes()

        if not self._ssh_command:
            log.error("No GitHub private key supplied; cannot push to GitHub.")
            return

        with self._git.git.custom_environment(GIT_SSH_COMMAND=self._ssh_command):
            self._git.remotes.origin.push()


@click_additional_options
@click.option(
    "--index-github-url",
    help="Repository URL on GitHub; needs to be SSH if you want to be able to write. (index=github only)",
    default="git@github.com:OpenTTD/BaNaNaS.git",
    show_default=True,
    metavar="URL",
)
@click.option(
    "--index-github-private-key",
    help="Base64-encoded private key to access GitHub."
    "Always use this via an environment variable!"
    "(index=github only)",
)
def click_index_github(index_github_url, index_github_private_key):
    global _github_url, _github_private_key

    _github_url = index_github_url
    if index_github_private_key:
        _github_private_key = base64.b64decode(index_github_private_key)
