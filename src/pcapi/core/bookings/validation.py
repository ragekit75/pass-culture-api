import datetime
from decimal import Decimal

from pcapi.core.bookings import api
from pcapi.core.bookings import conf
from pcapi.core.bookings import exceptions
from pcapi.core.bookings.models import Booking
from pcapi.core.offers.models import Offer
from pcapi.core.offers.models import Stock
from pcapi.core.users.models import ExpenseDomain
from pcapi.core.users.models import User
from pcapi.models import api_errors
from pcapi.models.db import db
from pcapi.repository import payment_queries


def check_can_book_free_offer(user: User, stock: Stock) -> None:
    # XXX: Despite its name, the intent of this function is to check
    # whether the user is allowed to book any offer (free or not
    # free), i.e. whether the user is a pro/admin or a "regular
    # user". Here we seem to allow pro/admin users to book non-free
    # offers, but in fact we'll check later whether the user has
    # money; since pro/admin users don't, an exception will be raised.
    if not user.isBeneficiary and stock.price == 0:
        raise exceptions.CannotBookFreeOffers()


def check_offer_already_booked(user: User, offer: Offer) -> None:
    """Raise ``OfferIsAlreadyBooked`` if the user already booked this offer."""
    if db.session.query(
        Booking.query.filter_by(
            user=user,
            isCancelled=False,
        )
        .join(Stock)
        .filter(Stock.offerId == offer.id)
        .exists()
    ).scalar():
        raise exceptions.OfferIsAlreadyBooked()


def check_quantity(offer: Offer, quantity: int) -> None:
    """May raise QuantityIsInvalid, depending on ``offer.isDuo``."""
    if offer.isDuo and quantity not in (1, 2):
        raise exceptions.QuantityIsInvalid("Vous devez réserver une place ou deux dans le cas d'une offre DUO.")

    if not offer.isDuo and quantity != 1:
        raise exceptions.QuantityIsInvalid("Vous ne pouvez réserver qu'une place pour cette offre.")


def check_stock_is_bookable(stock: Stock) -> None:
    if not stock.isBookable:
        raise exceptions.StockIsNotBookable()


def check_expenses_limits(user: User, requested_amount: Decimal, offer: Offer):
    """Raise an error if the requested amount would exceed the user's
    expense limits.
    """
    deposit = user.deposit
    if not deposit:
        raise exceptions.UserHasInsufficientFunds()
    if deposit.expirationDate and deposit.expirationDate < datetime.datetime.now():
        if requested_amount:
            raise exceptions.UserHasInsufficientFunds()

    config = conf.LIMIT_CONFIGURATIONS[deposit.version]
    for expense in user.expenses:
        if expense.domain == ExpenseDomain.ALL:
            if expense.current + requested_amount > expense.limit:
                raise exceptions.UserHasInsufficientFunds()

        if expense.domain == ExpenseDomain.DIGITAL and config.digital_cap_applies(offer):
            if expense.current + requested_amount > expense.limit:
                raise exceptions.DigitalExpenseLimitHasBeenReached(expense.limit)

        if expense.domain == ExpenseDomain.PHYSICAL and config.physical_cap_applies(offer):
            if expense.current + requested_amount > expense.limit:
                raise exceptions.PhysicalExpenseLimitHasBeenReached(expense.limit)


def check_beneficiary_can_cancel_booking(user: User, booking: Booking) -> None:
    if booking.userId != user.id:
        raise exceptions.BookingDoesntExist()
    if booking.isUsed:
        raise exceptions.BookingIsAlreadyUsed()
    if booking.isConfirmed:
        raise exceptions.CannotCancelConfirmedBooking(
            conf.BOOKING_CONFIRMATION_ERROR_CLAUSES["after_creation_delay"],
            conf.BOOKING_CONFIRMATION_ERROR_CLAUSES["before_event_delay"],
        )


# FIXME: should not raise exceptions from `api_errors` (see below for details).
def check_offerer_can_cancel_booking(booking: Booking) -> None:
    if booking.isCancelled:
        gone = api_errors.ResourceGoneError()
        gone.add_error("global", "Cette contremarque a déjà été annulée")
        raise gone
    if booking.isUsed:
        forbidden = api_errors.ForbiddenError()
        forbidden.add_error("global", "Impossible d'annuler une réservation consommée")
        raise forbidden


# FIXME (dbaty, 2020-10-19): I moved this function from validation/routes/bookings.py. It
# should not raise HTTP-related exceptions. It should rather raise
# generic exceptions such as `BookingIsAlreadyUsed` and the calling
# route should have an exception handler that turns it into the
# desired HTTP-related exception (such as ResourceGone and Forbidden)
# See also functions below.
def check_is_usable(booking: Booking) -> None:
    booking_payment = payment_queries.find_by_booking_id(booking.id)
    if booking_payment is not None:
        forbidden = api_errors.ForbiddenError()
        forbidden.add_error("payment", "Cette réservation a été remboursée")
        raise forbidden

    if booking.isUsed:
        gone = api_errors.ResourceGoneError()
        gone.add_error("booking", "Cette réservation a déjà été validée")
        raise gone

    if booking.isCancelled:
        forbidden = api_errors.ForbiddenError()
        forbidden.add_error("booking", "Cette réservation a été annulée")
        raise forbidden

    is_booking_for_event_and_not_confirmed = booking.stock.beginningDatetime and not booking.isConfirmed
    if is_booking_for_event_and_not_confirmed:
        forbidden = api_errors.ForbiddenError()
        booking_date = datetime.datetime.strftime(booking.dateCreated, "%d/%m/%Y à %H:%M")
        max_cancellation_date = datetime.datetime.strftime(
            api.compute_confirmation_date(booking.stock.beginningDatetime, booking.dateCreated), "%d/%m/%Y à %H:%M"
        )

        forbidden.add_error(
            "booking",
            f"Cette réservation a été effectuée le {booking_date}. "
            f"Veuillez attendre jusqu’au {max_cancellation_date} pour valider la contremarque.",
        )
        raise forbidden


# FIXME: should not raise exceptions from `api_errors` (see above for details).
def check_can_be_mark_as_unused(booking: Booking) -> None:
    if not booking.isUsed:
        gone = api_errors.ResourceGoneError()
        gone.add_error("booking", "Cette réservation n'a pas encore été validée")
        raise gone

    if booking.isCancelled:
        forbidden = api_errors.ForbiddenError()
        forbidden.add_error("booking", "Cette réservation a été annulée")
        raise forbidden

    booking_payment = payment_queries.find_by_booking_id(booking.id)
    if booking_payment is not None:
        gone = api_errors.ResourceGoneError()
        gone.add_error("payment", "Le remboursement est en cours de traitement")
        raise gone
