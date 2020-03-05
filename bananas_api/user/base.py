import datetime

from ..helpers.user_session import (
    delete_user,
    get_session_expire,
)


class User:
    method = None  # type: str

    def __init__(self, bearer_token, redirect_uri=None):
        self.bearer_token = bearer_token
        self.redirect_uri = redirect_uri

        self.display_name = None
        self.id = None

        self.expire = datetime.datetime.now() + datetime.timedelta(seconds=get_session_expire())

    @property
    def full_id(self):
        if self.id is None:
            return None

        return f"{self.method}:{self.id}"

    def is_logged_in(self):
        return self.id is not None

    def logout(self):
        delete_user(self)

    def check_expire(self):
        if datetime.datetime.now() > self.expire:
            self.logout()
            return None

        return self

    def get_authorize_url(self):
        raise NotImplementedError()
