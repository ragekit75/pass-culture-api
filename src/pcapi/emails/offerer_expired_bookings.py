import os
import typing

from pcapi.domain.postal_code.postal_code import PostalCode
from pcapi.models import Booking
from pcapi.models import Offerer
from pcapi.repository.feature_queries import feature_send_mail_to_users_enabled
from pcapi.utils.mailing import DEV_EMAIL_ADDRESS
from pcapi.utils.mailing import format_booking_date_for_email
from pcapi.utils.mailing import format_booking_hours_for_email


SUPPORT_EMAIL_ADDRESS = os.environ.get("SUPPORT_EMAIL_ADDRESS")


def build_expired_bookings_recap_email_data_for_offerer(
    offerer: Offerer, recipients: str, bookings: typing.List[Booking]
) -> typing.Dict:
    return {
        "FromEmail": SUPPORT_EMAIL_ADDRESS,
        "Mj-TemplateID": 1952508,
        "Mj-TemplateLanguage": True,
        "To": recipients if feature_send_mail_to_users_enabled() else DEV_EMAIL_ADDRESS,
        "Vars": {
            "bookings": _extract_bookings_information_from_bookings_list(bookings),
            "department": PostalCode(offerer.postalCode).get_departement_code(),
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
                "price": str(stock.price) if stock.price > 0 else "gratuit",
                "date": format_booking_date_for_email(booking),
                "time": format_booking_hours_for_email(booking),
                "quantity": booking.quantity,
                "user_name": booking.user.publicName,
                "user_email": booking.user.email,
            }
        )
    return bookings_info