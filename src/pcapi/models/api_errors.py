import json
from typing import Optional


class ApiErrors(Exception):
    def __init__(self, errors: dict = None):
        self.errors = errors if errors else {}

    def add_error(self, field, error) -> None:
        if field in self.errors:
            self.errors[field].append(error)
        else:
            self.errors[field] = [error]

    def check_min_length(self, field, value, length) -> None:
        if len(value) < length:
            self.add_error(field, 'Tu dois saisir au moins ' + str(length) + ' caractères.')

    def check_email(self, field, value) -> None:
        if not "@" in value:
            self.add_error(field, 'L’e-mail doit contenir un @.')

    def maybe_raise(self) -> None:
        if len(self.errors) > 0:
            raise self

    def __str__(self) -> None:
        if self.errors:
            return json.dumps(self.errors, indent=2)

    status_code: Optional[int] = None


class ResourceGoneError(ApiErrors):
    pass


class ResourceNotFoundError(ApiErrors):
    pass


class ForbiddenError(ApiErrors):
    pass


class DecimalCastError(ApiErrors):
    pass


class DateTimeCastError(ApiErrors):
    pass


class UuidCastError(ApiErrors):
    pass