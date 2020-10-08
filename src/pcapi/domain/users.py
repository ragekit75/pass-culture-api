from pcapi.models import UserSQLEntity


def check_is_authorized_to_access_bookings_recap(user: UserSQLEntity):
    if user.isAdmin:
        raise UnauthorizedForAdminUser()


class ClientError(Exception):
    def __init__(self, field: str, error: str):
        self.errors = {field: [error]}


class UnauthorizedForAdminUser(ClientError):
    def __init__(self):
        super().__init__('global',
                       "Le statut d'administrateur ne permet pas d'accéder au suivi des réservations")