from unittest.mock import patch

from tests.model_creators.generic_creators import create_offerer, create_bank_information, create_venue, create_stock, \
    create_user
from tests.model_creators.specific_creators import create_offer_with_thing_product, create_product_with_thing_type
from validation.models.entity_validator import validate


def test_should_return_errors_when_invalid_address():
    # Given
    offerer = create_offerer(postal_code="abcde")

    # When
    api_errors = validate(offerer)

    # Then
    assert api_errors.errors == {'postalCode': ['Ce code postal est invalide']}


def test_should_not_return_errors_when_valid_address():
    # Given
    offerer = create_offerer(postal_code="75000")

    # When
    api_errors = validate(offerer)

    # Then
    assert api_errors.errors == {}


def test_should_return_errors_when_invalid_bank_information():
    # Given
    bank_information = create_bank_information(bic="1234", iban="1234")

    # When
    api_errors = validate(bank_information)

    # Then
    assert api_errors.errors == {
        'bic': ['Le BIC renseigné ("1234") est invalide'],
        'iban': ['L’IBAN renseigné ("1234") est invalide']
    }


def test_should_not_return_errors_when_valid_bank_information():
    # Given
    bank_information = create_bank_information(bic="AGFBFRCC", iban="FR7014508000301971798194B82")

    # When
    api_errors = validate(bank_information)

    # Then
    assert api_errors.errors == {}


def test_should_return_errors_when_invalid_offer():
    # Given
    offerer = create_offerer()
    venue = create_venue(offerer, is_virtual=False)
    offer = create_offer_with_thing_product(venue, is_digital=True)

    # When
    api_errors = validate(offer)

    # Then
    assert api_errors.errors == {
        'venue': ['Une offre numérique doit obligatoirement être associée au lieu "Offre numérique"']
    }


def test_should_not_return_errors_when_valid_offer():
    # Given
    offerer = create_offerer()
    venue = create_venue(offerer, is_virtual=True)
    offer = create_offer_with_thing_product(venue, is_digital=True)

    # When
    api_errors = validate(offer)

    # Then
    assert api_errors.errors == {}


def test_should_return_errors_when_invalid_offerer():
    # Given
    offerer = create_offerer(siren="1")

    # When
    api_errors = validate(offerer)

    # Then
    assert api_errors.errors == {'siren': ['Ce code SIREN est invalide']}


def test_should_not_return_errors_when_valid_offerer():
    # Given
    offerer = create_offerer(siren="123456789")

    # When
    api_errors = validate(offerer)

    # Then
    assert api_errors.errors == {}


def test_should_return_errors_when_invalid_product():
    # Given
    product = create_product_with_thing_type(is_offline_only=True, is_digital=True)

    # When
    api_errors = validate(product)

    # Then
    assert api_errors.errors == {
        'url': ["Une offre de type Cinéma - cartes d'abonnement ne peut pas être "'numérique']
    }


def test_should_return_errors_when_valid_product():
    # Given
    product = create_product_with_thing_type()

    # When
    api_errors = validate(product)

    # Then
    assert api_errors.errors == {}


def test_should_return_errors_when_invalid_stock():
    # Given
    stock = create_stock(available=-1)

    # When
    api_errors = validate(stock)

    # Then
    assert api_errors.errors == {'available': ['Le stock doit être positif']}


def test_should_not_return_errors_when_valid_stock():
    # Given
    stock = create_stock(available=1)

    # When
    api_errors = validate(stock)

    # Then
    assert api_errors.errors == {}


@patch('validation.models.user.user_queries.count_users_by_email')
def test_should_return_errors_when_invalid_user(mock_count_users_by_email, app):
    # Given
    user = create_user(public_name='Jo')
    mock_count_users_by_email.return_value = 0

    # When
    api_errors = validate(user)

    # Then
    assert api_errors.errors == {'publicName': ['Vous devez saisir au moins 3 caractères.']}


@patch('validation.models.user.user_queries.count_users_by_email')
def test_should_not_return_errors_when_valid_user(mock_count_users_by_email, app):
    # Given
    user = create_user(public_name='Joe la bricole')
    mock_count_users_by_email.return_value = 0

    # When
    api_errors = validate(user)

    # Then
    assert api_errors.errors == {}


def test_should_return_errors_when_invalid_venue():
    # Given
    offerer = create_offerer()
    venue = create_venue(offerer, siret="123")

    # When
    api_errors = validate(venue)

    # Then
    assert api_errors.errors == {'siret': ['Ce code SIRET est invalide : 123']}


def test_should_not_return_errors_when_valid_venue():
    # Given
    offerer = create_offerer()
    venue = create_venue(offerer, siret="44229377500031")

    # When
    api_errors = validate(venue)

    # Then
    assert api_errors.errors == {}


def test_should_return_multiple_errors_when_invalid_offerer_and_address():
    # Given
    offerer = create_offerer(siren="1", postal_code="123")

    # When
    api_errors = validate(offerer)

    # Then
    assert api_errors.errors == {
        'postalCode': ['Ce code postal est invalide'],
        'siren': ['Ce code SIREN est invalide']
    }