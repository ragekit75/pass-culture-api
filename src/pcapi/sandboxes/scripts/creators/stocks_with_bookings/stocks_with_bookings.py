from datetime import datetime
from datetime import timedelta
from random import random

from sqlalchemy.exc import IntegrityError

import pcapi.core.bookings.factories as bookings_factories
import pcapi.core.offers.factories as offers_factories
import pcapi.core.users.factories as users_factories
from pcapi.model_creators.generic_creators import PLAIN_DEFAULT_TESTING_PASSWORD
from pcapi.utils.logger import logger


def random_datetime(min_date, max_date):
    return min_date + (max_date - min_date) * random()


def save_stocks_with_bookings_sandbox():
    admin = users_factories.UserFactory(isBeneficiary=False, isAdmin=True, email="pctest.admin93.0@example.com")
    admin.setPassword(PLAIN_DEFAULT_TESTING_PASSWORD)
    offerer = offers_factories.OffererFactory(name="AA - Structure de test")
    venue = offers_factories.VenueFactory(managingOfferer=offerer, name="AA - Lieu de test")
    event_offers = []
    thing_offers = []
    beneficiaries = []

    logger.info('Create 100 beneficiaries')
    for i in range(100):
        beneficiary = users_factories.UserFactory()
        beneficiaries.append(beneficiary)

    logger.info('Create 50 event offers')
    for i in range(50):
        offer = offers_factories.EventOfferFactory(venue=venue)
        event_offers.append(offer)

    logger.info('Create 50 thing offers')
    for i in range(50):
        offer = offers_factories.ThingOfferFactory(venue=venue)
        thing_offers.append(offer)

    logger.info('Create stocks for thing offers')
    for thing_offer in thing_offers:
        stock = offers_factories.ThingStockFactory(offer=thing_offer, quantity=100, price=0)

        logger.info('Create bookings for thing stock')
        for beneficiary in beneficiaries:
            create_booking(beneficiary, stock)

    logger.info('Create stocks for event offers')
    for event_offer in event_offers:
        now = datetime.utcnow()
        for i in range(10):
            stock_date = random_datetime(now - timedelta(days=30), now + timedelta(days=30))
            stock = offers_factories.EventStockFactory(offer=event_offer, beginningDatetime=stock_date, price=1)

            logger.info('Create bookings for event stock')
            for beneficiary in beneficiaries:
                create_booking(beneficiary, stock)


def create_booking(beneficiary, stock):
    try:
        bookings_factories.BookingFactory(user=beneficiary, stock=stock)
    except IntegrityError:
        logger.warning('Duplicate token, new try...')
        create_booking(beneficiary, stock)
