import typing

from pcapi.core.users.models import User
from pcapi.models import Booking


def build_expired_bookings_recap_email_data_for_beneficiary(
    beneficiary: User, bookings: typing.List[Booking]
) -> typing.Dict:
    return {
        "Mj-TemplateID": 1951103,
        "Mj-TemplateLanguage": True,
        "Vars": {
            "user_firstName": beneficiary.firstName,
            "bookings": _extract_bookings_information_from_bookings_list(bookings),
        },
    }


def _extract_bookings_information_from_bookings_list(bookings: typing.List[Booking]) -> typing.List[dict]:
    bookings_info = []
    for booking in bookings:
        stock = booking.stock
        offer = stock.offer
        bookings_info.append(
            {
                "offer_name": offer.name,
                "venue_name": offer.venue.publicName if offer.venue.publicName else offer.venue.name,
            }
        )
    return bookings_info
