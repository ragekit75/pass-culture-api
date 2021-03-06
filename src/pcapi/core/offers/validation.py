from datetime import datetime
from io import BytesIO
from typing import Optional
from typing import Union

from PIL import Image

from pcapi.models import Offer
from pcapi.models import Provider
from pcapi.models import Stock
from pcapi.models.api_errors import ApiErrors
from pcapi.models.api_errors import ForbiddenError
from pcapi.utils import requests as pcapi_requests

from . import exceptions


EDITABLE_FIELDS_FOR_OFFER_FROM_PROVIDER = {
    "audioDisabilityCompliant",
    "externalTicketOfficeUrl",
    "mentalDisabilityCompliant",
    "motorDisabilityCompliant",
    "visualDisabilityCompliant",
}
EDITABLE_FIELDS_FOR_ALLOCINE_OFFER = {"isDuo"} | EDITABLE_FIELDS_FOR_OFFER_FROM_PROVIDER
EDITABLE_FIELDS_FOR_ALLOCINE_STOCK = {"bookingLimitDatetime", "price", "quantity"}

MAX_THUMBNAIL_SIZE = 10_000_000
MIN_THUMBNAIL_WIDTH = 400
MIN_THUMBNAIL_HEIGHT = 400
ACCEPTED_THUMBNAIL_FORMATS = (
    "png",
    "jpg",
    "jpeg",
)
DISTANT_IMAGE_REQUEST_TIMEOUT = 5
CHUNK_SIZE_IN_BYTES = 4096


def check_user_can_create_activation_event(user):
    if not user.isAdmin:
        error = ForbiddenError()
        error.add_error("type", "Seuls les administrateurs du pass Culture peuvent créer des offres d'activation")
        raise error


def check_offer_is_editable(offer: Offer):
    if not offer.isEditable:
        error = ApiErrors()
        error.status_code = 400
        error.add_error("global", "Les offres importées ne sont pas modifiables")
        raise error


def check_update_only_allowed_fields_for_offer_from_provider(updated_fields: set, provider: Provider) -> None:
    if provider.isAllocine:
        rejected_fields = updated_fields - EDITABLE_FIELDS_FOR_ALLOCINE_OFFER
    else:
        rejected_fields = updated_fields - EDITABLE_FIELDS_FOR_OFFER_FROM_PROVIDER
    if rejected_fields:
        api_error = ApiErrors()
        for field in rejected_fields:
            api_error.add_error(field, "Vous ne pouvez pas modifier ce champ")

        raise api_error


def check_stocks_are_editable_for_offer(offer: Offer) -> None:
    if offer.isFromProvider:
        api_errors = ApiErrors()
        api_errors.add_error("global", "Les offres importées ne sont pas modifiables")
        raise api_errors


def check_stock_quantity(quantity: Union[int, None], bookingQuantity: int = 0) -> None:
    api_errors = ApiErrors()

    if quantity is not None and quantity < 0:
        api_errors.add_error("quantity", "Le stock doit être positif")

    if quantity is not None and bookingQuantity and (quantity - bookingQuantity) < 0:
        api_errors.add_error("quantity", "Le stock total ne peut être inférieur au nombre de réservations")

    if api_errors.errors:
        raise api_errors


def check_stock_price(price: float) -> None:
    if price < 0:
        api_errors = ApiErrors()
        api_errors.add_error("price", "Le prix doit être positif")
        raise api_errors


def check_required_dates_for_stock(
    offer: Offer,
    beginning: Optional[datetime],
    booking_limit_datetime: Optional[datetime],
) -> None:
    if offer.isThing:
        if beginning:
            raise ApiErrors(
                {
                    "global": [
                        "Impossible de mettre une date de début si l'offre ne porte pas sur un événement",
                    ]
                }
            )
    else:
        if not beginning:
            raise ApiErrors({"beginningDatetime": ["Ce paramètre est obligatoire"]})

        if not booking_limit_datetime:
            raise ApiErrors({"bookingLimitDatetime": ["Ce paramètre est obligatoire"]})


def check_stock_is_updatable(stock: Stock) -> None:
    check_offer_is_editable(stock.offer)

    if stock.isEventExpired:
        api_errors = ApiErrors()
        api_errors.add_error("global", "Les événements passés ne sont pas modifiables")
        raise api_errors


def check_stock_is_deletable(stock: Stock) -> None:
    check_offer_is_editable(stock.offer)

    if not stock.isEventDeletable:
        raise exceptions.TooLateToDeleteStock()


def check_update_only_allowed_stock_fields_for_allocine_offer(updated_fields: set) -> None:
    if not updated_fields.issubset(EDITABLE_FIELDS_FOR_ALLOCINE_STOCK):
        api_errors = ApiErrors()
        api_errors.status_code = 400
        api_errors.add_error("global", "Pour les offres importées, certains champs ne sont pas modifiables")
        raise api_errors


def check_mediation_thumb_quality(image_as_bytes: bytes) -> None:
    image = Image.open(BytesIO(image_as_bytes))
    if image.width < 400 or image.height < 400:
        raise ApiErrors({"thumb": ["L'image doit faire 400 * 400 px minimum"]})


def get_distant_image(
    url: str,
    accepted_types: tuple = ACCEPTED_THUMBNAIL_FORMATS,
    max_size: int = MAX_THUMBNAIL_SIZE,
) -> bytes:
    try:
        streaming_response = pcapi_requests.get(url, timeout=DISTANT_IMAGE_REQUEST_TIMEOUT, stream=True)
        streaming_response.raise_for_status()
    except Exception:
        raise exceptions.FailureToRetrieve()

    # These two headers are recommended to be included by the server, but they could be missing
    content_type = streaming_response.headers.get("Content-Type", "")
    if content_type and content_type.lstrip("image/") not in accepted_types:
        raise exceptions.UnacceptedFileType(accepted_types=accepted_types)

    content_length = streaming_response.headers.get("Content-Length", 0)
    if int(content_length) > max_size:
        raise exceptions.FileSizeExceeded(max_size=max_size)

    response_content = b""
    for chunk in streaming_response.iter_content(CHUNK_SIZE_IN_BYTES):
        response_content += chunk
        if len(response_content) > max_size:
            streaming_response.close()
            raise exceptions.FileSizeExceeded(max_size=max_size)
    return response_content


def get_uploaded_image(image_as_bytes: bytes, max_size: int = MAX_THUMBNAIL_SIZE) -> bytes:
    if len(image_as_bytes) > max_size:
        raise exceptions.FileSizeExceeded
    return image_as_bytes


def check_image(
    image_as_bytes: bytes,
    accepted_types: tuple = ACCEPTED_THUMBNAIL_FORMATS,
    min_width: int = MIN_THUMBNAIL_WIDTH,
    min_height: int = MIN_THUMBNAIL_HEIGHT,
) -> None:
    try:
        image = Image.open(BytesIO(image_as_bytes))
    except Exception:
        raise exceptions.UnacceptedFileType(accepted_types)

    if image.format.lower() not in accepted_types:
        raise exceptions.UnacceptedFileType(accepted_types)

    if image.width < min_width or image.height < min_height:
        raise exceptions.ImageTooSmall(min_width, min_height)
