from typing import List
from typing import Optional

from flask import current_app as app
from flask import request
from flask_login import current_user
from flask_login import login_required

from pcapi.connectors import redis
from pcapi.connectors.thumb_storage import create_thumb
from pcapi.connectors.thumb_storage import read_thumb
from pcapi.core.offers.models import Mediation
from pcapi.flask_app import private_api
from pcapi.models.feature import FeatureToggle
from pcapi.models.user_offerer import RightsType
from pcapi.repository import feature_queries
from pcapi.repository import repository
from pcapi.routes.serialization.mediations_serialize import CreateMediationBodyModel
from pcapi.routes.serialization.mediations_serialize import MediationResponseIdModel
from pcapi.routes.serialization.mediations_serialize import UpdateMediationBodyModel
from pcapi.routes.serialization.mediations_serialize import UpdateMediationResponseModel
from pcapi.serialization.decorator import spectree_serialize
from pcapi.utils.human_ids import dehumanize
from pcapi.utils.rest import ensure_current_user_has_rights
from pcapi.utils.rest import load_or_404
from pcapi.validation.routes.mediations import check_thumb_in_request
from pcapi.validation.routes.mediations import check_thumb_quality


@private_api.route("/mediations", methods=["POST"])
@login_required
@spectree_serialize(on_success_status=201, response_model=MediationResponseIdModel)
def create_mediation(form: CreateMediationBodyModel) -> MediationResponseIdModel:
    check_thumb_in_request(files=request.files, form=form)
    ensure_current_user_has_rights(RightsType.editor, form.offerer_id)
    mediation = Mediation()
    mediation.author = current_user
    mediation.offerId = form.offer_id
    mediation.credit = form.credit
    mediation.offererId = form.offerer_id
    thumb = read_thumb(files=request.files, form=form)
    check_thumb_quality(thumb)
    repository.save(mediation)
    create_thumb(mediation, thumb, 0, crop_params=_get_crop(form))
    mediation.thumbCount = 1
    repository.save(mediation)
    if feature_queries.is_active(FeatureToggle.SYNCHRONIZE_ALGOLIA):
        redis.add_offer_id(client=app.redis_client, offer_id=form.offer_id)
    return MediationResponseIdModel.from_orm(mediation)


@private_api.route("/mediations/<mediation_id>", methods=["PATCH"])
@login_required
@spectree_serialize(on_success_status=200, response_model=UpdateMediationResponseModel)
def update_mediation(mediation_id: str, body: UpdateMediationBodyModel) -> UpdateMediationResponseModel:
    mediation = load_or_404(Mediation, mediation_id)
    ensure_current_user_has_rights(RightsType.editor, mediation.offer.venue.managingOffererId)
    mediation = Mediation.query.filter_by(id=dehumanize(mediation_id)).first()
    mediation.populate_from_dict(body.dict())
    repository.save(mediation)
    if feature_queries.is_active(FeatureToggle.SYNCHRONIZE_ALGOLIA):
        redis.add_offer_id(client=app.redis_client, offer_id=mediation.offerId)
    return UpdateMediationResponseModel.from_orm(mediation)


def _get_crop(form: CreateMediationBodyModel) -> Optional[List[float]]:
    if form.cropping_rect_x is not None and form.cropping_rect_y is not None and form.cropping_rect_height is not None:
        return [form.cropping_rect_x, form.cropping_rect_y, form.cropping_rect_height]

    return None