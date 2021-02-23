import pytest

from pcapi.model_creators.generic_creators import create_bank_information
from pcapi.model_creators.generic_creators import create_offerer
from pcapi.model_creators.generic_creators import create_user
from pcapi.model_creators.generic_creators import create_user_offerer
from pcapi.model_creators.generic_creators import create_venue
from pcapi.repository import repository
import pcapi.core.users.factories as users_factories
import pcapi.core.offerers.factories as offerers_factories
from pcapi.core.offers.factories import VenueFactory
from pcapi.utils.human_ids import humanize

from tests.conftest import TestClient


class Get:
    class Returns200:
        @pytest.mark.usefixtures("db_session")
        def when_user_has_rights_on_managing_offerer(self, app):
            # given
            venue = VenueFactory(name="L'encre et la plume")
            user = users_factories.UserFactory(email="user@example.com")

            auth_request = TestClient(app.test_client()).with_auth(email=user.email)

            # when
            response = auth_request.get("/venues/%s/stats" % humanize(venue.id))

            # then
            assert response.status_code == 200
            response_json = response.json
            assert response_json["activeBookingsCount"] == 123

    class Returns403:
        @pytest.mark.usefixtures("db_session")
        def when_current_user_doesnt_have_rights(self, app):
            # given
            offerer = create_offerer()
            user = create_user(email="user.pro@test.com")
            venue = create_venue(offerer, name="L'encre et la plume")
            repository.save(user, venue)
            auth_request = TestClient(app.test_client()).with_auth(email=user.email)

            # when
            response = auth_request.get("/venues/%s/stats" % humanize(venue.id))

            # then
            assert response.status_code == 403
            assert response.json["global"] == [
                "Vous n'avez pas les droits d'accès suffisant pour accéder à cette information."
            ]
