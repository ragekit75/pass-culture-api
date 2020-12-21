import pytest

from pcapi.core.users import exceptions
from pcapi.core.users import factories
from pcapi.core.users import repository


class CheckUserAndCredentialsTest:
    def test_unknown_user(self):
        with pytest.raises(exceptions.InvalidIdentifier):
            repository._check_user_and_credentials(None, "doe")

    def test_with_inactive_user(self):
        user = factories.UserFactory.build(isActive=False)
        with pytest.raises(exceptions.InvalidIdentifier):
            repository._check_user_and_credentials(user, factories.DEFAULT_PASSWORD)

    def test_user_pending_validation(self):
        user = factories.UserFactory.build(isActive=True, validationToken="123")
        with pytest.raises(exceptions.UnvalidatedAccount):
            repository._check_user_and_credentials(user, factories.DEFAULT_PASSWORD)

    def test_user_pending_email_validation(self):
        user = factories.UserFactory.build(isActive=True, isEmailValidated=False)
        with pytest.raises(exceptions.UnvalidatedAccount):
            repository._check_user_and_credentials(user, factories.DEFAULT_PASSWORD)

    def test_user_with_invalid_password(self):
        user = factories.UserFactory.build(isActive=True)
        with pytest.raises(exceptions.InvalidPassword):
            repository._check_user_and_credentials(user, "123")

    def test_user_with_valid_password(self):
        user = factories.UserFactory.build(isActive=True)
        repository._check_user_and_credentials(user, factories.DEFAULT_PASSWORD)