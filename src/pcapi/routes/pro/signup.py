from flask import request

from pcapi.core.users.api import create_pro_user
from pcapi.flask_app import private_api
from pcapi.routes.serialization.users import ProUserCreationBodyModel
from pcapi.serialization.decorator import spectree_serialize


@private_api.route("/users/signup/pro", methods=["POST"])
@spectree_serialize(on_success_status=204)
def signup_pro(body: ProUserCreationBodyModel) -> None:
    create_pro_user(request)
