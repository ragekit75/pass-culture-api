from datetime import datetime
from datetime import timedelta
from unittest.mock import patch

from flask_jwt_extended import decode_token
from flask_jwt_extended.utils import create_access_token
from freezegun import freeze_time
import pytest

from pcapi.core.testing import override_features
from pcapi.core.users import factories as users_factories
from pcapi.core.users.models import Token
from pcapi.core.users.models import TokenType
from pcapi.core.users.models import hash_password
from pcapi.repository import repository
from pcapi.repository.user_queries import find_user_by_id
from pcapi.utils.token import random_token

from tests.conftest import TestClient


pytestmark = pytest.mark.usefixtures("db_session")


def test_user_logs_in_and_refreshes_token(app):
    data = {"identifier": "user@test.com", "password": users_factories.DEFAULT_PASSWORD}
    user = users_factories.UserFactory(email=data["identifier"], password=data["password"])
    test_client = TestClient(app.test_client())

    # Get the refresh and access token
    response = test_client.post("/native/v1/signin", json=data)
    assert response.status_code == 200
    assert response.json["refreshToken"]
    assert response.json["accessToken"]

    refresh_token = response.json["refreshToken"]
    access_token = response.json["accessToken"]

    # Ensure the access token is valid
    test_client.auth_header = {"Authorization": f"Bearer {access_token}"}
    response = test_client.get("/native/v1/me")
    assert response.status_code == 200

    # Ensure the access token contains user.id
    decoded = decode_token(access_token)
    assert decoded["user_claims"]["user_id"] == user.id

    # Ensure the refresh token can generate a new access token
    test_client.auth_header = {"Authorization": f"Bearer {refresh_token}"}
    response = test_client.post("/native/v1/refresh_access_token", json={})
    assert response.status_code == 200, response.json
    assert response.json["accessToken"]
    access_token = response.json["accessToken"]

    # Ensure the new access token is valid
    test_client.auth_header = {"Authorization": f"Bearer {access_token}"}
    response = test_client.get("/native/v1/me")
    assert response.status_code == 200

    # Ensure the new access token contains user.id
    decoded = decode_token(access_token)
    assert decoded["user_claims"]["user_id"] == user.id


def test_user_logs_in_with_wrong_password(app):
    data = {"identifier": "user@test.com", "password": users_factories.DEFAULT_PASSWORD}
    users_factories.UserFactory(email=data["identifier"], password=data["password"])
    test_client = TestClient(app.test_client())

    # signin with invalid password and ensures the result messsage is generic
    data["password"] = data["password"][:-2]
    response = test_client.post("/native/v1/signin", json=data)
    assert response.status_code == 400
    assert response.json == {"general": ["Identifiant ou Mot de passe incorrect"]}


def test_unknown_user_logs_in(app):
    data = {"identifier": "user@test.com", "password": users_factories.DEFAULT_PASSWORD}
    test_client = TestClient(app.test_client())

    # signin with invalid password and ensures the result messsage is generic
    response = test_client.post("/native/v1/signin", json=data)
    assert response.status_code == 400
    assert response.json == {"general": ["Identifiant ou Mot de passe incorrect"]}


def test_user_logs_in_with_missing_fields(app):
    test_client = TestClient(app.test_client())

    response = test_client.post("/native/v1/signin", json={})
    assert response.status_code == 400
    assert response.json == {
        "identifier": ["Ce champ est obligatoire"],
        "password": ["Ce champ est obligatoire"],
    }


def test_send_reset_password_email_without_email(app):
    response = TestClient(app.test_client()).post("/native/v1/request_password_reset")

    assert response.status_code == 400
    assert response.json["email"] == ["Ce champ est obligatoire"]


def test_request_reset_password_for_unknown_email(app):
    data = {"email": "not_existing_user@example.com"}
    response = TestClient(app.test_client()).post("/native/v1/request_password_reset", json=data)

    assert response.status_code == 204


@patch("pcapi.domain.user_emails.send_reset_password_email_to_native_app_user")
@patch("pcapi.connectors.api_recaptcha.check_native_app_recaptcha_token")
@override_features(ENABLE_NATIVE_APP_RECAPTCHA=True)
def test_request_reset_password_with_recaptcha_ok(
    mock_check_native_app_recaptcha_token,
    mock_send_reset_password_email_to_native_app_user,
    app,
):
    email = "existing_user@example.com"
    data = {"email": email}
    user = users_factories.UserFactory(email=email)

    saved_token = Token.query.filter_by(user=user).first()
    assert saved_token is None

    mock_send_reset_password_email_to_native_app_user.return_value = True
    mock_check_native_app_recaptcha_token.return_value = None

    response = TestClient(app.test_client()).post("/native/v1/request_password_reset", json=data)

    mock_send_reset_password_email_to_native_app_user.assert_called_once()
    mock_check_native_app_recaptcha_token.assert_called_once()
    assert response.status_code == 204

    saved_token = Token.query.filter_by(user=user).first()
    assert saved_token.type.value == "reset-password"


@patch("pcapi.domain.user_emails.send_reset_password_email_to_native_app_user")
def test_request_reset_password_for_existing_email(mock_send_reset_password_email_to_native_app_user, app):
    email = "existing_user@example.com"
    data = {"email": email}
    user = users_factories.UserFactory(email=email)

    saved_token = Token.query.filter_by(user=user).first()
    assert saved_token is None

    mock_send_reset_password_email_to_native_app_user.return_value = True

    response = TestClient(app.test_client()).post("/native/v1/request_password_reset", json=data)

    mock_send_reset_password_email_to_native_app_user.assert_called_once()
    assert response.status_code == 204

    saved_token = Token.query.filter_by(user=user).first()
    assert saved_token.type.value == "reset-password"


@patch("pcapi.domain.user_emails.send_reset_password_email_to_native_app_user")
def test_request_reset_password_for_inactive_account(mock_send_reset_password_email_to_native_app_user, app):
    email = "existing_user@example.com"
    data = {"email": email}
    users_factories.UserFactory(email=email, isActive=False)

    response = TestClient(app.test_client()).post("/native/v1/request_password_reset", json=data)

    assert response.status_code == 204
    mock_send_reset_password_email_to_native_app_user.assert_not_called()


@patch("pcapi.domain.user_emails.send_reset_password_email_to_native_app_user")
def test_request_reset_password_with_mail_service_exception(mock_send_reset_password_email_to_native_app_user, app):
    email = "existing_user@example.com"
    data = {"email": email}
    users_factories.UserFactory(email=email)

    mock_send_reset_password_email_to_native_app_user.return_value = False

    response = TestClient(app.test_client()).post("/native/v1/request_password_reset", json=data)

    mock_send_reset_password_email_to_native_app_user.assert_called_once()
    assert response.status_code == 400
    assert response.json["email"] == ["L'email n'a pas pu être envoyé"]


def test_reset_password_with_not_valid_token(app):
    data = {"reset_password_token": "unknwon_token", "new_password": "new_password"}
    user = users_factories.UserFactory()
    old_password = user.password

    response = TestClient(app.test_client()).post("/native/v1/reset_password", json=data)

    assert response.status_code == 400
    assert user.password == old_password


def test_reset_password_success(app):
    new_password = "New_password1998!"

    user = users_factories.UserFactory()

    token = Token(from_dict={"userId": user.id, "value": "secret-value", "type": TokenType.RESET_PASSWORD})
    repository.save(token)

    data = {"reset_password_token": token.value, "new_password": new_password}
    response = TestClient(app.test_client()).post("/native/v1/reset_password", json=data)

    user = find_user_by_id(user.id)
    assert response.status_code == 204
    assert user.password == hash_password(new_password)


def test_reset_password_for_unvalidated_email(app):
    new_password = "New_password1998!"

    user = users_factories.UserFactory(isEmailValidated=False)

    token = Token(from_dict={"userId": user.id, "value": "secret-value", "type": TokenType.RESET_PASSWORD})
    repository.save(token)

    data = {"reset_password_token": token.value, "new_password": new_password}
    response = TestClient(app.test_client()).post("/native/v1/reset_password", json=data)

    user = find_user_by_id(user.id)
    assert response.status_code == 204
    assert user.password == hash_password(new_password)
    assert user.isEmailValidated


def test_reset_password_fail_for_password_strength(app):
    reset_token = random_token()
    user = users_factories.UserFactory(
        resetPasswordToken=reset_token,
        resetPasswordTokenValidityLimit=(datetime.utcnow() + timedelta(hours=1)),
    )
    old_password = user.password
    new_password = "weak_password"

    data = {"reset_password_token": reset_token, "new_password": new_password}

    response = TestClient(app.test_client()).post("/native/v1/reset_password", json=data)

    user = find_user_by_id(user.id)
    assert response.status_code == 400
    assert user.password == old_password


def test_change_password_success(app):
    new_password = "New_password1998!"
    user = users_factories.UserFactory()

    access_token = create_access_token(identity=user.email)
    test_client = TestClient(app.test_client())
    test_client.auth_header = {"Authorization": f"Bearer {access_token}"}

    response = test_client.post(
        "/native/v1/change_password",
        json={"currentPassword": users_factories.DEFAULT_PASSWORD, "newPassword": new_password},
    )

    assert response.status_code == 204
    user = find_user_by_id(user.id)
    assert user.password == hash_password(new_password)


def test_change_password_failures(app):
    new_password = "New_password1998!"
    user = users_factories.UserFactory()

    access_token = create_access_token(identity=user.email)
    test_client = TestClient(app.test_client())
    test_client.auth_header = {"Authorization": f"Bearer {access_token}"}

    response = test_client.post(
        "/native/v1/change_password",
        json={"currentPassword": "wrong_password", "newPassword": new_password},
    )

    assert response.status_code == 400
    assert response.json["code"] == "INVALID_PASSWORD"

    response = test_client.post(
        "/native/v1/change_password",
        json={"currentPassword": users_factories.DEFAULT_PASSWORD, "newPassword": "weak_password"},
    )

    assert response.status_code == 400
    assert response.json["code"] == "WEAK_PASSWORD"

    user = find_user_by_id(user.id)
    assert user.password == hash_password(users_factories.DEFAULT_PASSWORD)


@patch("pcapi.core.users.repository.get_user_with_valid_token", return_value=None)
def test_validate_email_with_invalid_token(mock_get_user_with_valid_token, app):
    token = "email-validation-token"

    response = TestClient(app.test_client()).post("/native/v1/validate_email", json={"email_validation_token": token})

    mock_get_user_with_valid_token.assert_called_once_with(token, [TokenType.EMAIL_VALIDATION])

    assert response.status_code == 400


@freeze_time("2018-06-01")
def test_validate_email_when_eligible(app):
    user = users_factories.UserFactory(isEmailValidated=False, dateOfBirth=datetime(2000, 6, 1))
    token = users_factories.TokenFactory(userId=user.id, type=TokenType.EMAIL_VALIDATION)

    assert not user.isEmailValidated

    test_client = TestClient(app.test_client())
    response = test_client.post("/native/v1/validate_email", json={"email_validation_token": token.value})

    id_check_token = response.json["idCheckToken"]

    assert user.isEmailValidated
    assert response.status_code == 200
    assert id_check_token

    # Ensure the id_check_token generated is valid
    saved_token = Token.query.filter_by(value=id_check_token).first()
    assert saved_token.type == TokenType.ID_CHECK
    assert saved_token.userId == user.id

    # Ensure the access token is valid
    access_token = response.json["accessToken"]
    test_client.auth_header = {"Authorization": f"Bearer {access_token}"}
    protected_response = test_client.get("/native/v1/me")
    assert protected_response.status_code == 200

    # Ensure the access token contains user.id
    decoded = decode_token(access_token)
    assert decoded["user_claims"]["user_id"] == user.id

    # Ensure the refresh token is valid
    refresh_token = response.json["refreshToken"]
    test_client.auth_header = {"Authorization": f"Bearer {refresh_token}"}
    refresh_response = test_client.post("/native/v1/refresh_access_token", json={})
    assert refresh_response.status_code == 200


@freeze_time("2018-06-01")
def test_validate_email_when_not_eligible(app):
    user = users_factories.UserFactory(isEmailValidated=False, dateOfBirth=datetime(2000, 7, 1))
    token = users_factories.TokenFactory(userId=user.id, type=TokenType.EMAIL_VALIDATION)

    assert not user.isEmailValidated

    test_client = TestClient(app.test_client())
    response = test_client.post("/native/v1/validate_email", json={"email_validation_token": token.value})

    assert user.isEmailValidated
    assert response.status_code == 200
    assert response.json["idCheckToken"] is None

    # Ensure the access token is valid
    access_token = response.json["accessToken"]
    test_client.auth_header = {"Authorization": f"Bearer {access_token}"}
    protected_response = test_client.get("/native/v1/me")
    assert protected_response.status_code == 200

    # Ensure the refresh token is valid
    refresh_token = response.json["refreshToken"]
    test_client.auth_header = {"Authorization": f"Bearer {refresh_token}"}
    refresh_response = test_client.post("/native/v1/refresh_access_token", json={})
    assert refresh_response.status_code == 200
