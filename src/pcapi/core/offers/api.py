import datetime
from typing import List
from typing import Optional
from typing import Union

from flask import current_app as app
import pytz
from sqlalchemy.sql.functions import func

from pcapi.connectors import redis
from pcapi.connectors.thumb_storage import create_thumb
from pcapi.connectors.thumb_storage import remove_thumb
import pcapi.core.bookings.repository as bookings_repository
import pcapi.core.offers.repository as offers_repository
from pcapi.core.users.models import User
from pcapi.domain import admin_emails
from pcapi.domain import user_emails
from pcapi.domain.pro_offers.paginated_offers_recap import PaginatedOffersRecap
from pcapi.models import EventType
from pcapi.models import Offer
from pcapi.models import Product
from pcapi.models import Stock
from pcapi.models import Venue
from pcapi.models import db
from pcapi.models.api_errors import ApiErrors
from pcapi.models.feature import FeatureToggle
from pcapi.repository import feature_queries
from pcapi.repository import mediation_queries
from pcapi.repository import offer_queries
from pcapi.repository import repository
from pcapi.routes.serialization.offers_serialize import PostOfferBodyModel
from pcapi.routes.serialization.stock_serialize import StockCreationBodyModel
from pcapi.routes.serialization.stock_serialize import StockEditionBodyModel
from pcapi.utils import mailing
from pcapi.utils.rest import check_user_has_access_to_offerer
from pcapi.utils.rest import load_or_raise_error

from . import validation
from ..bookings.api import mark_as_unused
from ..bookings.api import update_confirmation_dates
from ..bookings.models import Booking
from .exceptions import ThumbnailStorageError
from .models import Mediation


DEFAULT_OFFERS_PER_PAGE = 10
DEFAULT_PAGE = 1
UNCHANGED = object()


def list_offers_for_pro_user(
    user_id: int,
    user_is_admin: bool,
    type_id: Optional[str],
    offerer_id: Optional[int],
    offers_per_page: Optional[int],
    page: Optional[int],
    venue_id: Optional[int] = None,
    name_keywords: Optional[str] = None,
    status: Optional[str] = None,
    creation_mode: Optional[str] = None,
    period_beginning_date: Optional[str] = None,
    period_ending_date: Optional[str] = None,
) -> PaginatedOffersRecap:
    return offers_repository.get_paginated_offers_for_filters(
        user_id=user_id,
        user_is_admin=user_is_admin,
        offerer_id=offerer_id,
        offers_per_page=offers_per_page or DEFAULT_OFFERS_PER_PAGE,
        venue_id=venue_id,
        type_id=type_id,
        page=page or DEFAULT_PAGE,
        name_keywords=name_keywords,
        status=status,
        creation_mode=creation_mode,
        period_beginning_date=period_beginning_date,
        period_ending_date=period_ending_date,
    )


def create_offer(offer_data: PostOfferBodyModel, user: User) -> Offer:
    venue = load_or_raise_error(Venue, offer_data.venue_id)

    check_user_has_access_to_offerer(user, offerer_id=venue.managingOffererId)

    if offer_data.product_id:
        product = load_or_raise_error(Product, offer_data.product_id)
        offer = Offer(
            product=product,
            type=product.type,
            name=product.name,
            description=product.description,
            url=product.url,
            mediaUrls=product.mediaUrls,
            conditions=product.conditions,
            ageMin=product.ageMin,
            ageMax=product.ageMax,
            durationMinutes=product.durationMinutes,
            isNational=product.isNational,
            extraData=product.extraData,
        )
    else:
        if offer_data.type == str(EventType.ACTIVATION):
            validation.check_user_can_create_activation_event(user)
        data = offer_data.dict(by_alias=True)
        product = Product()
        if data.get("url"):
            data["isNational"] = True
        product.populate_from_dict(data)
        offer = Offer()
        offer.populate_from_dict(data)
        offer.product = product
        offer.product.owningOfferer = venue.managingOfferer

    offer.venue = venue
    offer.bookingEmail = offer_data.booking_email
    offer.externalTicketOfficeUrl = offer_data.external_ticket_office_url
    offer.audioDisabilityCompliant = offer_data.audio_disability_compliant
    offer.mentalDisabilityCompliant = offer_data.mental_disability_compliant
    offer.motorDisabilityCompliant = offer_data.motor_disability_compliant
    offer.visualDisabilityCompliant = offer_data.visual_disability_compliant
    repository.save(offer)
    admin_emails.send_offer_creation_notification_to_administration(offer, user)

    return offer


def update_offer(  # pylint: disable=redefined-builtin
    offer: Offer,
    bookingEmail: str = UNCHANGED,
    description: str = UNCHANGED,
    isNational: bool = UNCHANGED,
    name: str = UNCHANGED,
    extraData: dict = UNCHANGED,
    type: str = UNCHANGED,
    externalTicketOfficeUrl: str = UNCHANGED,
    url: str = UNCHANGED,
    withdrawalDetails: str = UNCHANGED,
    isActive: bool = UNCHANGED,
    isDuo: bool = UNCHANGED,
    durationMinutes: int = UNCHANGED,
    mediaUrls: List[str] = UNCHANGED,
    ageMin: int = UNCHANGED,
    ageMax: int = UNCHANGED,
    conditions: str = UNCHANGED,
    venueId: str = UNCHANGED,
    productId: str = UNCHANGED,
    audioDisabilityCompliant: bool = UNCHANGED,
    mentalDisabilityCompliant: bool = UNCHANGED,
    motorDisabilityCompliant: bool = UNCHANGED,
    visualDisabilityCompliant: bool = UNCHANGED,
) -> Offer:
    # fmt: off
    modifications = {
        field: new_value
        for field, new_value in locals().items()
        if field != 'offer'
        and new_value is not UNCHANGED  # has the user provided a value for this field
        and getattr(offer, field) != new_value  # is the value different from what we have on database?
    }
    # fmt: on
    if not modifications:
        return offer

    if offer.isFromProvider:
        validation.check_update_only_allowed_fields_for_offer_from_provider(set(modifications), offer.lastProvider)

    offer.populate_from_dict(modifications)
    if offer.product.owningOfferer and offer.product.owningOfferer == offer.venue.managingOfferer:
        offer.product.populate_from_dict(modifications)
        product_has_been_updated = True
    else:
        product_has_been_updated = False

    if offer.isFromAllocine:
        offer.fieldsUpdated = list(set(offer.fieldsUpdated) | set(modifications))

    repository.save(offer)
    if product_has_been_updated:
        repository.save(offer.product)

    if feature_queries.is_active(FeatureToggle.SYNCHRONIZE_ALGOLIA):
        redis.add_offer_id(client=app.redis_client, offer_id=offer.id)

    return offer


def update_offers_active_status(query, is_active):
    # We cannot just call `query.update()` because `distinct()` may
    # already have been called on `query`.
    query_to_update = Offer.query.filter(Offer.id.in_(query.with_entities(Offer.id)))
    query_to_update.update({"isActive": is_active}, synchronize_session=False)
    db.session.commit()

    if feature_queries.is_active(FeatureToggle.SYNCHRONIZE_ALGOLIA):
        offer_ids = {offer_id for offer_id, in query.with_entities(Offer.id)}
        for offer_id in offer_ids:
            redis.add_offer_id(client=app.redis_client, offer_id=offer_id)


def _create_stock(
    offer: Offer,
    price: float,
    quantity: int = None,
    beginning: datetime.datetime = None,
    booking_limit_datetime: datetime.datetime = None,
) -> Stock:
    validation.check_required_dates_for_stock(offer, beginning, booking_limit_datetime)
    validation.check_offer_is_editable(offer)
    validation.check_stocks_are_editable_for_offer(offer)
    validation.check_stock_price(price)
    validation.check_stock_quantity(quantity)

    return Stock(
        offer=offer,
        price=price,
        quantity=quantity,
        beginningDatetime=beginning,
        bookingLimitDatetime=booking_limit_datetime,
    )


def _edit_stock(
    stock: Stock,
    price: float,
    quantity: int,
    beginning: datetime.datetime,
    booking_limit_datetime: datetime.datetime,
) -> Stock:
    validation.check_stock_is_updatable(stock)
    validation.check_required_dates_for_stock(stock.offer, beginning, booking_limit_datetime)
    validation.check_stock_price(price)
    validation.check_stock_quantity(quantity, stock.bookingsQuantity)

    # FIXME (dbaty, 2020-11-25): We need this ugly workaround because
    # the frontend sends us datetimes like "2020-12-03T14:00:00Z"
    # (note the "Z" suffix). Pydantic deserializes it as a datetime
    # *with* a timezone. However, datetimes are stored in the database
    # as UTC datetimes *without* any timezone. Thus, we wrongly detect
    # a change for the "beginningDatetime" field for Allocine stocks:
    # because we do not allow it to be changed, we raise an error when
    # we should not.
    def as_utc_without_timezone(d: datetime.datetime) -> datetime.datetime:
        return d.astimezone(pytz.utc).replace(tzinfo=None)

    if beginning:
        beginning = as_utc_without_timezone(beginning)
    if booking_limit_datetime:
        booking_limit_datetime = as_utc_without_timezone(booking_limit_datetime)

    updates = {
        "price": price,
        "quantity": quantity,
        "beginningDatetime": beginning,
        "bookingLimitDatetime": booking_limit_datetime,
    }

    if stock.offer.isFromAllocine:
        # fmt: off
        updated_fields = {
            attr
            for attr, new_value in updates.items()
            if new_value != getattr(stock, attr)
        }
        # fmt: on
        validation.check_update_only_allowed_stock_fields_for_allocine_offer(updated_fields)
        stock.fieldsUpdated = list(updated_fields)

    for model_attr, value in updates.items():
        setattr(stock, model_attr, value)

    return stock


def _notify_beneficiaries_upon_stock_edit(stock: Stock):
    bookings = bookings_repository.find_not_cancelled_bookings_by_stock(stock)
    if bookings:
        bookings = update_confirmation_dates(bookings, stock.beginningDatetime)
        date_in_two_days = datetime.datetime.utcnow() + datetime.timedelta(days=2)
        check_event_is_in_more_than_48_hours = stock.beginningDatetime > date_in_two_days
        if check_event_is_in_more_than_48_hours:
            bookings = _invalidate_bookings(bookings)
        try:
            user_emails.send_batch_stock_postponement_emails_to_users(bookings)
        except mailing.MailServiceException as exc:
            # fmt: off
            app.logger.exception(
                "Could not notify beneficiaries about update of stock=%s: %s",
                stock.id,
                exc,
            )
            # fmt: on


def upsert_stocks(
    offer_id: int, stock_data_list: List[Union[StockCreationBodyModel, StockEditionBodyModel]]
) -> List[Stock]:
    stocks = []
    edited_stocks = []
    edited_stocks_previous_beginnings = {}

    offer = offer_queries.get_offer_by_id(offer_id)

    for stock_data in stock_data_list:
        if isinstance(stock_data, StockEditionBodyModel):
            stock = Stock.queryNotSoftDeleted().filter_by(id=stock_data.id).first_or_404()
            if stock.offerId != offer_id:
                errors = ApiErrors()
                errors.add_error(
                    "global", "Vous n'avez pas les droits d'accès suffisant pour accéder à cette information."
                )
                errors.status_code = 403
                raise errors
            edited_stocks_previous_beginnings[stock.id] = stock.beginningDatetime
            edited_stock = _edit_stock(
                stock,
                price=stock_data.price,
                quantity=stock_data.quantity,
                beginning=stock_data.beginning_datetime,
                booking_limit_datetime=stock_data.booking_limit_datetime,
            )
            edited_stocks.append(edited_stock)
            stocks.append(edited_stock)
        else:
            created_stock = _create_stock(
                offer=offer,
                price=stock_data.price,
                quantity=stock_data.quantity,
                beginning=stock_data.beginning_datetime,
                booking_limit_datetime=stock_data.booking_limit_datetime,
            )
            stocks.append(created_stock)

    repository.save(*stocks)

    for stock in edited_stocks:
        previous_beginning = edited_stocks_previous_beginnings[stock.id]
        if stock.beginningDatetime != previous_beginning:
            _notify_beneficiaries_upon_stock_edit(stock)
    if feature_queries.is_active(FeatureToggle.SYNCHRONIZE_ALGOLIA):
        redis.add_offer_id(client=app.redis_client, offer_id=offer.id)

    return stocks


def _invalidate_bookings(bookings: List[Booking]) -> List[Booking]:
    for booking in bookings:
        if booking.isUsed:
            mark_as_unused(booking)
    return bookings


def delete_stock(stock: Stock) -> None:
    validation.check_stock_is_deletable(stock)

    stock.isSoftDeleted = True

    cancelled_bookings = []
    for booking in stock.bookings:
        if not booking.isCancelled and not booking.isUsed:
            booking.isCancelled = True
            cancelled_bookings.append(booking)

    repository.save(stock, *cancelled_bookings)

    if cancelled_bookings:
        try:
            user_emails.send_batch_cancellation_emails_to_users(cancelled_bookings)
        except mailing.MailServiceException as exc:
            app.logger.exception("Could not notify beneficiaries about deletion of stock=%s: %s", stock.id, exc)
        try:
            user_emails.send_offerer_bookings_recap_email_after_offerer_cancellation(cancelled_bookings)
        except mailing.MailServiceException as exc:
            app.logger.exception("Could not notify offerer about deletion of stock=%s: %s", stock.id, exc)

    if feature_queries.is_active(FeatureToggle.SYNCHRONIZE_ALGOLIA):
        redis.add_offer_id(client=app.redis_client, offer_id=stock.offerId)


# TODO(fseguin): cleanup after v2 is launched
def create_mediation(
    user: User,
    offer: Offer,
    credit: str,
    image_as_bytes: bytes,
    crop_params: tuple = None,
) -> Mediation:
    validation.check_mediation_thumb_quality(image_as_bytes)

    mediation = Mediation(
        author=user,
        offer=offer,
        credit=credit,
    )
    # `create_thumb()` requires the object to have an id, so we must save now.
    repository.save(mediation)

    create_thumb(mediation, image_as_bytes, image_index=0, crop_params=crop_params)
    mediation.thumbCount = 1
    repository.save(mediation)

    if feature_queries.is_active(FeatureToggle.SYNCHRONIZE_ALGOLIA):
        redis.add_offer_id(client=app.redis_client, offer_id=offer.id)

    return mediation


# TODO(fseguin): cleanup after v2 is launched
def update_mediation(mediation: Mediation, is_active: bool) -> Mediation:
    mediation.isActive = is_active
    repository.save(mediation)

    if feature_queries.is_active(FeatureToggle.SYNCHRONIZE_ALGOLIA):
        redis.add_offer_id(client=app.redis_client, offer_id=mediation.offerId)

    return mediation


def create_mediation_v2(
    user: User,
    offer: Offer,
    credit: str,
    image_as_bytes: bytes,
    crop_params: tuple = None,
) -> Mediation:
    # checks image type, min dimensions
    validation.check_image(image_as_bytes)

    existing_mediations = mediation_queries.get_mediations_for_offers([offer.id])

    mediation = Mediation(
        author=user,
        offer=offer,
        credit=credit,
    )
    # `create_thumb()` requires the object to have an id, so we must save now.
    repository.save(mediation)

    try:
        # TODO(fseguin): cleanup after image upload v2 launch
        create_thumb(mediation, image_as_bytes, image_index=0, crop_params=crop_params, use_v2=True)

    except Exception as exc:
        app.logger.exception("An unexpected error was encountered during the thumbnail creation: %s", exc)
        # I could not use savepoints and rollbacks with SQLA
        repository.delete(mediation)
        raise ThumbnailStorageError

    else:
        mediation.thumbCount = 1
        repository.save(mediation)
        # cleanup former thumbnails and mediations
        for previous_mediation in existing_mediations:
            try:
                for thumb_index in range(0, mediation.thumbCount):
                    remove_thumb(previous_mediation, image_index=thumb_index)
            except Exception as exc:  # pylint: disable=broad-except
                app.logger.exception(
                    "An unexpected error was encountered during the thumbnails deletion for %s: %s",
                    mediation,
                    exc,
                )
            else:
                repository.delete(previous_mediation)

        if feature_queries.is_active(FeatureToggle.SYNCHRONIZE_ALGOLIA):
            redis.add_offer_id(client=app.redis_client, offer_id=offer.id)

        return mediation


def update_offer_and_stock_id_at_providers(venue: Venue, old_siret: str) -> None:
    current_siret = venue.siret

    offer_ids = (
        Offer.query.filter(Offer.venueId == venue.id)
        .filter(Offer.idAtProviders.endswith(old_siret))
        .with_entities(Offer.id)
        .all()
    )
    stock_ids = (
        Stock.query.join(Offer)
        .filter(Offer.venueId == venue.id)
        .filter(Stock.idAtProviders.endswith(old_siret))
        .with_entities(Stock.id)
        .all()
    )

    batch_size = 100

    for offer_index in range(0, len(offer_ids), batch_size):
        Offer.query.filter(Offer.id.in_(offer_ids[offer_index : offer_index + batch_size])).update(
            {Offer.idAtProviders: func.replace(Offer.idAtProviders, old_siret, current_siret)},
            synchronize_session=False,
        )
        db.session.commit()
        offer_index = offer_index + batch_size

    for stock_index in range(0, len(stock_ids), batch_size):
        Stock.query.filter(Stock.id.in_(stock_ids[stock_index : stock_index + batch_size])).update(
            {Stock.idAtProviders: func.replace(Stock.idAtProviders, old_siret, current_siret)},
            synchronize_session=False,
        )
        db.session.commit()
        stock_index = stock_index + batch_size
