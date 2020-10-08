import random
from typing import List, Optional

from sqlalchemy.orm import joinedload

from pcapi.models import DiscoveryView, MediationSQLEntity, OfferSQLEntity, Recommendation, UserSQLEntity, VenueSQLEntity
from pcapi.models.db import db
from pcapi.recommendations_engine import get_offers_for_recommendations_discovery
from pcapi.repository import mediation_queries, repository
from pcapi.repository.offer_queries import find_searchable_offer, get_offers_for_recommendation_v3
from pcapi.repository.recommendation_queries import find_recommendation_already_created_on_discovery
from pcapi.utils.logger import logger


# TODO remove this function and its tests once v3 is the only route
def give_requested_recommendation_to_user(user, offer_id, mediation_id):
    recommendation = None

    if mediation_id or offer_id:
        recommendation = find_recommendation_already_created_on_discovery(
            offer_id, mediation_id, user.id)
        if recommendation is None:
            with db.session.no_autoflush:
                recommendation = _create_recommendation_from_ids(user, offer_id, mediation_id=mediation_id)
            repository.save(recommendation)
            logger.debug(lambda: 'Creating Recommendation with offer_id=%s mediation_id=%s' % (offer_id, mediation_id))

    return recommendation


def create_recommendations_for_discovery(user: UserSQLEntity,
                                         sent_offers_ids: List[int] = [],
                                         limit: int = 3) -> List[Recommendation]:
    recommendations = []

    offers = get_offers_for_recommendations_discovery(
        limit=limit,
        user=user,
        sent_offers_ids=sent_offers_ids
    )

    for (index, offer) in enumerate(offers):
        recommendations.append(_create_recommendation_from_offers(user, offer))
    repository.save(*recommendations)
    return recommendations


def create_recommendations_for_discovery_v3(user: UserSQLEntity, user_iris_id: Optional[int] = None,
                                            user_is_geolocated: bool = False, sent_offers_ids: List[int] = [],
                                            limit: int = 3) -> List[Recommendation]:
    recommendations = []

    offers = get_offers_for_recommendation_v3(user=user, user_iris_id=user_iris_id,
                                              user_is_geolocated=user_is_geolocated, limit=limit,
                                              sent_offers_ids=sent_offers_ids)

    for (index, offer) in enumerate(offers):
        recommendations.append(_create_recommendation_from_offers(user, offer))
    repository.save(*recommendations)

    recommendation_ids = [recommendation.id for recommendation in recommendations]

    return _get_recommendation_with_information(recommendation_ids)


def _get_recommendation_with_information(recommendation_ids: List[int]) -> List[Recommendation]:
    return Recommendation.query \
        .filter(
            Recommendation.id.in_(recommendation_ids)) \
        .options(
            joinedload(Recommendation.offer)
            .joinedload(OfferSQLEntity.venue)
            .joinedload(VenueSQLEntity.managingOfferer)) \
        .options(
            joinedload(Recommendation.offer)
            .joinedload(OfferSQLEntity.stocks)) \
        .options(
            joinedload(Recommendation.offer)
            .joinedload(OfferSQLEntity.mediations)) \
        .all()


def _create_recommendation_from_ids(user, offer_id, mediation_id=None):
    mediation = None

    if mediation_id:
        mediation = mediation_queries.find_by_id(mediation_id)

    offer = mediation.offer if mediation else find_searchable_offer(offer_id)

    return _create_recommendation(user, offer, mediation=mediation)


def _create_recommendation(user: UserSQLEntity, offer: OfferSQLEntity,
                           mediation: MediationSQLEntity = None) -> Recommendation:
    recommendation = Recommendation()
    recommendation.user = user

    recommendation.offer = offer

    if mediation:
        recommendation.mediation = mediation
    else:
        active_mediations = [m for m in offer.mediations if m.isActive]
        if active_mediations:
            recommendation.mediation = random.choice(active_mediations)

    return recommendation


# TODO: when using discovery view use this function instead of _create_recommendation
# in create_recommendations_for_discovery
def _create_recommendation_from_offers(user: UserSQLEntity, reco_view: DiscoveryView,
                                       mediation: MediationSQLEntity = None) -> Recommendation:
    recommendation = Recommendation()
    recommendation.user = user

    recommendation.offerId = reco_view.id

    if mediation:
        recommendation.mediation = mediation
    else:
        recommendation.mediationId = reco_view.mediationId
    return recommendation