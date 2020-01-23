from models import Deposit
from repository import repository
from tests.conftest import clean_database
from tests.model_creators.generic_creators import create_user


@clean_database
def test_deposit_creation_1(app):
    # given
    user = create_user()

    deposit = Deposit()
    deposit.user = user
    deposit.amount = 200
    deposit.source = "test money"

    # when
    repository.save(deposit)

    # then
    assert Deposit.query.count() == 1


@clean_database
def test_deposit_creation_2(app):
    # given
    user = create_user()

    deposit = Deposit()
    deposit.user = user
    deposit.amount = 200
    deposit.source = "test money"

    # when
    repository.save(deposit)

    # then
    assert Deposit.query.count() == 1
