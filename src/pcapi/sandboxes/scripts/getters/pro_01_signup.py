from pcapi.core.users.models import User
from pcapi.models.user_offerer import UserOfferer
from pcapi.sandboxes.scripts.utils.helpers import get_offerer_helper
from pcapi.sandboxes.scripts.utils.helpers import get_pro_helper


def get_existing_pro_user_with_offerer():
    query = User.query.join(UserOfferer)
    user = query.first()

    offerer = [uo.offerer for uo in user.UserOfferers][0]

    return {"offerer": get_offerer_helper(offerer), "user": get_pro_helper(user)}


def get_existing_pro_not_validated_user_with_real_offerer():
    users = User.query.filter(User.validationToken is not None).join(UserOfferer).all()

    for user in users:
        if len(user.UserOfferers) == 1:
            return {"user": get_pro_helper(user)}
    return None
