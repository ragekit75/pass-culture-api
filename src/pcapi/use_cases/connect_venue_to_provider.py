from typing import Callable
from typing import Dict
from typing import Optional

from pcapi.domain.stock_provider.stock_provider_repository import StockProviderRepository
from pcapi.local_providers import FnacStocks
from pcapi.local_providers import LibrairesStocks
from pcapi.local_providers import PraxielStocks
from pcapi.local_providers import TiteLiveStocks
from pcapi.models import ApiErrors
from pcapi.models import Venue
from pcapi.models import VenueProvider
from pcapi.repository import repository
from pcapi.utils.human_ids import dehumanize
from pcapi.validation.routes.venues import check_existing_venue


STANDARD_STOCK_PROVIDERS = {
    FnacStocks: "FNAC",
    LibrairesStocks: "LesLibraires",
    PraxielStocks: "Praxiel/Inférence",
    TiteLiveStocks: "TiteLive",
}
ERROR_CODE_PROVIDER_NOT_SUPPORTED = 400
ERROR_CODE_SIRET_NOT_SUPPORTED = 422


def connect_venue_to_provider(
    provider_class: object,
    stock_provider_repository: StockProviderRepository,
    venue_provider_payload: Dict,
    find_venue_by_id: Callable,
) -> VenueProvider:
    venue_id = dehumanize(venue_provider_payload["venueId"])
    venue = find_venue_by_id(venue_id)
    check_existing_venue(venue)
    if provider_class not in STANDARD_STOCK_PROVIDERS:
        api_errors = ApiErrors()
        api_errors.status_code = ERROR_CODE_PROVIDER_NOT_SUPPORTED
        api_errors.add_error("provider", "Provider non pris en charge")
        raise api_errors

    _check_venue_can_be_synchronized_with_provider(
        venue.siret, stock_provider_repository.can_be_synchronized, STANDARD_STOCK_PROVIDERS[provider_class]
    )
    new_venue_provider = _connect_stock_providers_to_venue(venue, venue_provider_payload)
    return new_venue_provider


def _connect_stock_providers_to_venue(venue: Venue, venue_provider_payload: Dict) -> VenueProvider:
    venue_provider = VenueProvider()
    venue_provider.venue = venue
    venue_provider.providerId = dehumanize(venue_provider_payload["providerId"])
    venue_provider.venueIdAtOfferProvider = venue.siret

    repository.save(venue_provider)
    return venue_provider


def _check_venue_can_be_synchronized_with_provider(
    siret: str, can_be_synchronized: Callable, provider_name: str
) -> None:
    if not siret or not can_be_synchronized(siret):
        api_errors = ApiErrors()
        api_errors.status_code = ERROR_CODE_SIRET_NOT_SUPPORTED
        api_errors.add_error("provider", _get_synchronization_error_message(provider_name, siret))
        raise api_errors


def _get_synchronization_error_message(provider_name: str, siret: Optional[str]) -> str:
    if siret:
        return f"L’importation d’offres avec {provider_name} n’est pas disponible pour le SIRET {siret}"
    return f"L’importation d’offres avec {provider_name} n’est pas disponible sans SIRET associé au lieu. Ajoutez un SIRET pour pouvoir importer les offres."
