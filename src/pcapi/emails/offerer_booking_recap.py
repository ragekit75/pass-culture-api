from typing import Dict

from pcapi.core.bookings.models import Booking
from pcapi.models.offer_type import ProductType
from pcapi.utils.mailing import build_pc_pro_offer_link
from pcapi.utils.mailing import format_booking_date_for_email
from pcapi.utils.mailing import format_booking_hours_for_email


def retrieve_data_for_offerer_booking_recap_email(booking: Booking) -> Dict:
    offer = booking.stock.offer
    venue_name = offer.venue.name
    offer_name = offer.name
    price = "Gratuit" if booking.stock.price == 0 else str(booking.stock.price)
    quantity = booking.quantity
    user_email = booking.user.email
    user_firstname = booking.user.firstName
    user_lastname = booking.user.lastName
    user_phoneNumber = booking.user.phoneNumber or ""
    departement_code = offer.venue.departementCode or "numérique"
    offer_type = offer.type
    is_event = int(offer.isEvent)
    can_expire = int(offer.offerType.get("canExpire", False))

    offer_link = build_pc_pro_offer_link(offer)

    mailjet_json = {
        "MJ-TemplateID": 2418750,
        "MJ-TemplateLanguage": True,
        "Headers": {
            "Reply-To": user_email,
        },
        "Vars": {
            "nom_offre": offer_name,
            "nom_lieu": venue_name,
            "is_event": is_event,
            "ISBN": "",
            "offer_type": "book",
            "date": "",
            "heure": "",
            "quantity": quantity,
            "contremarque": booking.token,
            "prix": price,
            "user_firstName": user_firstname,
            "user_lastName": user_lastname,
            "user_phoneNumber": user_phoneNumber,
            "user_email": user_email,
            "lien_offre_pcpro": offer_link,
            "departement": departement_code,
            "can_expire": can_expire,
        },
    }

    offer_is_a_book = ProductType.is_book(offer_type)

    if offer_is_a_book:
        mailjet_json["Vars"]["ISBN"] = (
            offer.extraData["isbn"] if offer.extraData is not None and "isbn" in offer.extraData else ""
        )
    else:
        mailjet_json["Vars"]["offer_type"] = offer_type

    offer_is_an_event = is_event == 1
    if offer_is_an_event:
        mailjet_json["Vars"]["date"] = format_booking_date_for_email(booking)
        mailjet_json["Vars"]["heure"] = format_booking_hours_for_email(booking)

    return mailjet_json
