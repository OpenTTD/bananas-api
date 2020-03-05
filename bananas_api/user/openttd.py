from .base import User as BaseUser


class User(BaseUser):
    method = "openttd"

    # TODO -- Implement OpenTTD login

    def get_authorize_url(self):
        raise NotImplementedError()
