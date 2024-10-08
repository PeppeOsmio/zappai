from uuid import UUID


class UserNotFoundError(Exception):
    pass


class UsernameExistsError(Exception):
    pass


class EmailExistsError(Exception):
    pass


class InvalidCursorError(Exception):
    pass
