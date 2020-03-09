from datetime import datetime

from models import Booking
from repository import repository
from scripts.booking.canceling_token_validation import canceling_token_validation
from tests.conftest import clean_database
from tests.model_creators.generic_creators import create_booking, \
    create_deposit, create_offerer, create_payment, create_user


@clean_database
def test_should_update_booking_when_valid_token_is_given_and_no_payment_associated(app):
    # Given
    token = '123456'
    beneficiary = create_user()
    create_deposit(user=beneficiary)
    invalid_booking = create_booking(date_used=datetime(2020, 1, 1), is_used=True, token=token, user=beneficiary)
    repository.save(invalid_booking)

    # When
    canceling_token_validation(token=token)

    # Then
    booking = Booking.query.first()
    assert booking.token == '123456'
    assert booking.isUsed is False
    assert booking.dateUsed is None


@clean_database
def test_should_doing_nothing_when_valid_token_is_given_but_there_is_a_payment_already(app):
    # Given
    token = '123456'
    beneficiary = create_user()
    create_deposit(user=beneficiary)
    invalid_booking = create_booking(date_used=datetime(2020, 1, 1), is_used=True, token=token, user=beneficiary)
    offerer = create_offerer()
    payment = create_payment(booking=invalid_booking, offerer=offerer)
    repository.save(payment)

    # When
    canceling_token_validation(token=token)

    # Then
    booking = Booking.query.first()
    assert booking.token == '123456'
    assert booking.isUsed is True
    assert booking.dateUsed == datetime(2020, 1, 1)