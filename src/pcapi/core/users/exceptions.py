class CredentialsException(Exception):
    pass


class InvalidIdentifier(CredentialsException):
    pass


class UnvalidatedAccount(CredentialsException):
    pass


class UserAlreadyExistsException(Exception):
    pass


class NotEligible(Exception):
    pass


class UnderAgeUserException(Exception):
    pass


class EmailNotSent(Exception):
    pass
