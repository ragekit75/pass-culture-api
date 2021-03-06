import subprocess

from flask import jsonify
from flask import request
from flask_login import login_required

from pcapi.domain.stock_provider.stock_provider_repository import StockProviderRepository
from pcapi.flask_app import private_api
from pcapi.infrastructure.container import api_fnac_stocks
from pcapi.infrastructure.container import api_libraires_stocks
from pcapi.infrastructure.container import api_praxiel_stocks
from pcapi.infrastructure.container import api_titelive_stocks
import pcapi.local_providers
from pcapi.local_providers import AllocineStocks
from pcapi.local_providers import FnacStocks
from pcapi.local_providers import LibrairesStocks
from pcapi.local_providers import PraxielStocks
from pcapi.local_providers.titelive_stocks.titelive_stocks import TiteLiveStocks
from pcapi.models.api_errors import ApiErrors
from pcapi.models.feature import FeatureToggle
from pcapi.models.venue_provider import VenueProvider
from pcapi.repository import feature_queries
from pcapi.repository.allocine_pivot_queries import get_allocine_theaterId_for_venue
from pcapi.repository.provider_queries import get_provider_enabled_for_pro_by_id
from pcapi.repository.venue_queries import find_by_id
from pcapi.routes.serialization import as_dict
from pcapi.use_cases.connect_venue_to_allocine import connect_venue_to_allocine
from pcapi.use_cases.connect_venue_to_provider import connect_venue_to_provider
from pcapi.utils.human_ids import dehumanize
from pcapi.utils.includes import VENUE_PROVIDER_INCLUDES
from pcapi.utils.rest import expect_json_data
from pcapi.validation.routes.venue_providers import check_existing_provider
from pcapi.validation.routes.venue_providers import check_new_venue_provider_information
from pcapi.workers.venue_provider_job import venue_provider_job


# @debt api-migration
@private_api.route("/venueProviders", methods=["GET"])
@login_required
def list_venue_providers():
    venue_id = request.args.get("venueId")
    if venue_id is None:
        e = ApiErrors()
        e.add_error("venueId", "Vous devez obligatoirement fournir le paramètre venueId")
        return jsonify(e.errors), 400

    vp_query = VenueProvider.query.filter_by(venueId=dehumanize(venue_id))
    return jsonify([as_dict(venue_provider, includes=VENUE_PROVIDER_INCLUDES) for venue_provider in vp_query.all()])


# @debt api-migration
@private_api.route("/venueProviders", methods=["POST"])
@login_required
@expect_json_data
def create_venue_provider():
    venue_provider_payload = request.json
    check_new_venue_provider_information(venue_provider_payload)

    provider_id = dehumanize(venue_provider_payload["providerId"])
    provider = get_provider_enabled_for_pro_by_id(provider_id)
    check_existing_provider(provider)

    provider_class = getattr(pcapi.local_providers, provider.localClass)
    if provider_class == AllocineStocks:
        new_venue_provider = connect_venue_to_allocine(
            venue_provider_payload, find_by_id, get_allocine_theaterId_for_venue
        )
    else:
        stock_provider_repository = _get_stock_provider_repository(provider_class)
        new_venue_provider = connect_venue_to_provider(
            provider_class, stock_provider_repository, venue_provider_payload, find_by_id
        )

    _run_first_synchronization(new_venue_provider)

    return jsonify(as_dict(new_venue_provider, includes=VENUE_PROVIDER_INCLUDES)), 201


def _get_stock_provider_repository(provider_class) -> StockProviderRepository:
    providers = {
        LibrairesStocks: api_libraires_stocks,
        FnacStocks: api_fnac_stocks,
        TiteLiveStocks: api_titelive_stocks,
        PraxielStocks: api_praxiel_stocks,
    }
    return providers.get(provider_class, None)


def _run_first_synchronization(new_venue_provider: VenueProvider):
    if not feature_queries.is_active(FeatureToggle.SYNCHRONIZE_VENUE_PROVIDER_IN_WORKER):
        subprocess.Popen(
            [
                "python",
                "src/pcapi/scripts/pc.py",
                "update_providables",
                "--venue-provider-id",
                str(new_venue_provider.id),
            ]
        )
        return

    venue_provider_job.delay(new_venue_provider.id)
