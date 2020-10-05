import click
import git

from openttd_helpers import click_helper

from .common_disk import Index as CommonDiskIndex

_folder = None
_username = None
_email = None


class Index(CommonDiskIndex):
    def __init__(self):
        super().__init__(_folder)

        self._git_author = git.Actor(_username, _email)

    def prepare(self):
        try:
            self._git = git.Repo(self.folder)
        except git.exc.NoSuchPathError:
            self._init_repository()
        except git.exc.InvalidGitRepositoryError:
            self._init_repository()

    def _init_repository(self):
        self._git = git.Repo.init(self.folder)
        # Always make sure there is a commit in the working tree, otherwise
        # HEAD is invalid, which results in other nasty problems.
        self._git.index.commit(
            "Add: initial empty commit",
            author=self._git_author,
            committer=self._git_author,
        )

    def commit(self):
        files = self.files[:]
        self.files = []

        change = self.change
        self.change = None

        for filename in files:
            self._git.index.add(filename)

        # Check if there was anything to commit; possibly someone changed an
        # edit back to the original, meaning we are about to commit an empty
        # commit. That would be silly of course.
        if not self._git.index.diff("HEAD"):
            return

        commit_message = f"Update: {change}"

        self._git.index.commit(
            commit_message,
            author=self._git_author,
            committer=self._git_author,
        )


@click_helper.extend
@click.option(
    "--index-local-folder",
    help="Folder to use for index storage. (index=local only)",
    type=click.Path(dir_okay=True, file_okay=False),
    default="BaNaNaS",
    show_default=True,
)
@click.option(
    "--index-local-username", help="Username to use when creating commits.", default="Librarian", show_default=True
)
@click.option(
    "--index-local-email",
    help="Email to use when creating commits.",
    default="content-api@openttd.org",
    show_default=True,
)
def click_index_local(index_local_folder, index_local_username, index_local_email):
    global _folder, _username, _email

    _folder = index_local_folder
    _username = index_local_username
    _email = index_local_email
