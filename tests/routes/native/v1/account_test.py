from unittest.mock import patch

from flask_jwt_extended.utils import create_access_token
import pytest

from pcapi.core.users import factories as users_factories
from pcapi.models import UserSQLEntity

from tests.conftest import TestClient


pytestmark = pytest.mark.usefixtures("db_session")


class AccountTest:
    identifier = "email@example.com"

    def test_get_user_profile_without_authentication(self, app):
        users_factories.UserFactory(email=self.identifier)

        response = TestClient(app.test_client()).get("/native/v1/me")

        assert response.status_code == 401

    def test_get_user_profile_not_found(self, app):
        users_factories.UserFactory(email=self.identifier)

        access_token = create_access_token(identity="other-email@example.com")
        test_client = TestClient(app.test_client())
        test_client.auth_header = {"Authorization": f"Bearer {access_token}"}

        response = test_client.get("/native/v1/me")

        assert response.status_code == 400
        assert response.json["email"] == ["Utilisateur introuvable"]

    def test_get_user_profile(self, app):
        first_name = "Gaëtan"
        users_factories.UserFactory(email=self.identifier, firstName=first_name)

        access_token = create_access_token(identity=self.identifier)
        test_client = TestClient(app.test_client())
        test_client.auth_header = {"Authorization": f"Bearer {access_token}"}

        response = test_client.get("/native/v1/me")

        assert response.status_code == 200
        assert response.json["email"] == self.identifier
        assert response.json["first_name"] == first_name

    def test_get_user_profile_empty_first_name(self, app):
        first_name = ""
        users_factories.UserFactory(email=self.identifier, firstName=first_name)

        access_token = create_access_token(identity=self.identifier)
        test_client = TestClient(app.test_client())
        test_client.auth_header = {"Authorization": f"Bearer {access_token}"}

        response = test_client.get("/native/v1/me")

        assert response.status_code == 200
        assert response.json["email"] == self.identifier
        assert response.json["first_name"] is None

    @patch("pcapi.domain.beneficiary.beneficiary_licence.is_licence_token_valid", return_value=True)
    @patch("pcapi.utils.mailing.send_raw_email", return_value=True)
    def test_account_creation(self, mocked_send_raw_email, mocked_is_licence_token_valid, app):
        test_client = TestClient(app.test_client())
        assert UserSQLEntity.query.first() is None
        data = {
            "email": "john.doe@example.com",
            "password": "Aazflrifaoi6@",
            "birthdate": "1960-12-31",
            "notifications": True,
            "token": "gnagna",
            "hasAllowedRecommendations": True,
        }

        response = test_client.post("/native/v1/account", json=data)
        assert response.status_code == 204, response.json

        user = UserSQLEntity.query.first()
        assert user is not None
        assert user.email == data["email"]
        assert user.isEmailValidated is False
        mocked_send_raw_email.assert_called()