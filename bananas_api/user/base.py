import base64
import datetime
import hashlib
import secrets

from ..helpers.user_session import (
    create_bearer_token,
    delete_user,
    handover_to_bearer,
    get_login_expire,
    get_session_expire,
)


class User:
    method = None  # type: str

    def __init__(self, redirect_uri, code_challenge):
        self.redirect_uri = redirect_uri
        self.code_challenge = code_challenge

        self.code = secrets.token_hex(16)
        self.login_expire = datetime.datetime.now() + datetime.timedelta(seconds=get_login_expire())

        self.bearer_token = None
        self.session_expire = None
        self.display_name = None
        self.id = None

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
        if self.login_expire and datetime.datetime.now() > self.login_expire:
            self.logout()
            return None

        if self.session_expire and datetime.datetime.now() > self.session_expire:
            self.logout()
            return None

        return self

    def validate(self, code_verifier):
        digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        if code_challenge != self.code_challenge:
            return False

        self.bearer_token = create_bearer_token()
        self.session_expire = datetime.datetime.now() + datetime.timedelta(seconds=get_session_expire())

        handover_to_bearer(self, self.bearer_token)

        self.code = None
        self.login_expire = None

        return True

    def get_authorize_page(self):
        raise NotImplementedError()
