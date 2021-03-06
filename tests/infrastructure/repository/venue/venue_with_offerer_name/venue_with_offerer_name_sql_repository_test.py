import pytest

from pcapi.domain.identifier.identifier import Identifier
from pcapi.domain.venue.venue_with_offerer_name.venue_with_offerer_name import VenueWithOffererName
from pcapi.infrastructure.repository.venue.venue_with_offerer_name import venue_with_offerer_name_domain_converter
from pcapi.infrastructure.repository.venue.venue_with_offerer_name.venue_with_offerer_name_sql_repository import (
    VenueWithOffererNameSQLRepository,
)
from pcapi.model_creators.generic_creators import create_offerer
from pcapi.model_creators.generic_creators import create_user
from pcapi.model_creators.generic_creators import create_user_offerer
from pcapi.model_creators.generic_creators import create_venue
from pcapi.repository import repository


class GetByProIdentifierTest:
    def setup_method(self):
        self.venue_sql_repository = VenueWithOffererNameSQLRepository()

    @pytest.mark.usefixtures("db_session")
    def should_return_only_venues_of_pro_user(self, app: object):
        # given
        pro_user = create_user()
        offerer = create_offerer()
        other_offerer = create_offerer(siren="987654321")
        create_user_offerer(user=pro_user, offerer=offerer)
        venue_1 = create_venue(offerer=offerer, siret="12345678912345")
        venue_2 = create_venue(offerer=offerer, siret="12345678998765")
        venue_not_affiliated_to_pro_user = create_venue(offerer=other_offerer, siret="98765432198765")

        repository.save(venue_1, venue_2, venue_not_affiliated_to_pro_user)

        expected_venue_1 = venue_with_offerer_name_domain_converter.to_domain(venue_1)
        expected_venue_2 = venue_with_offerer_name_domain_converter.to_domain(venue_2)

        # when
        found_venues = self.venue_sql_repository.get_by_pro_identifier(pro_user.id, False)

        # then
        assert len(found_venues) == 2
        assert isinstance(found_venues[0], VenueWithOffererName)
        found_venues_id = [venue.identifier for venue in found_venues]
        assert set(found_venues_id) == {expected_venue_1.identifier, expected_venue_2.identifier}

    @pytest.mark.usefixtures("db_session")
    def should_return_all_existing_venues_for_admin_user(self, app: object):
        # given
        admin_user = create_user(is_admin=True)
        offerer = create_offerer()
        other_offerer = create_offerer(siren="987654321")
        venue_1 = create_venue(offerer=offerer, siret="12345678912345")
        venue_2 = create_venue(offerer=other_offerer, siret="98765432198765")

        repository.save(venue_1, venue_2)

        expected_venue_1 = venue_with_offerer_name_domain_converter.to_domain(venue_1)
        expected_venue_2 = venue_with_offerer_name_domain_converter.to_domain(venue_2)

        # when
        found_venues = self.venue_sql_repository.get_by_pro_identifier(admin_user.id, True)

        # then
        assert len(found_venues) == 2
        assert isinstance(found_venues[0], VenueWithOffererName)
        found_venues_id = [venue.identifier for venue in found_venues]
        assert set(found_venues_id) == {expected_venue_1.identifier, expected_venue_2.identifier}

    @pytest.mark.usefixtures("db_session")
    def should_return_empty_list_when_no_venues_exist(self, app: object):
        # given
        pro_user = create_user()
        offerer = create_offerer()
        user_offerer = create_user_offerer(user=pro_user, offerer=offerer)
        repository.save(user_offerer)

        # when
        found_venues = self.venue_sql_repository.get_by_pro_identifier(pro_user.id, False)

        # then
        assert found_venues == []

    @pytest.mark.usefixtures("db_session")
    def should_return_all_venues_of_pro_user_ordered_by_name(self, app: object):
        # given
        pro_user = create_user()
        offerer = create_offerer()
        create_user_offerer(user=pro_user, offerer=offerer)
        venue_1 = create_venue(offerer=offerer, siret="12345678912345", name="B")
        venue_2 = create_venue(offerer=offerer, siret="98765432198765", name="A")

        repository.save(venue_1, venue_2)

        expected_venue_1 = venue_with_offerer_name_domain_converter.to_domain(venue_1)
        expected_venue_2 = venue_with_offerer_name_domain_converter.to_domain(venue_2)

        # when
        found_venues = self.venue_sql_repository.get_by_pro_identifier(pro_user.id, False)

        # then
        assert len(found_venues) == 2
        assert found_venues[0].name == expected_venue_2.name
        assert found_venues[1].name == expected_venue_1.name

    @pytest.mark.usefixtures("db_session")
    def should_not_return_venues_of_non_validated_offerer(self, app: object):
        # given
        pro_user = create_user()
        offerer_validated = create_offerer(siren="123456789")
        offerer_not_validated = create_offerer(siren="987654321", validation_token="TOKEN")
        create_user_offerer(user=pro_user, offerer=offerer_validated)
        create_user_offerer(user=pro_user, offerer=offerer_not_validated, validation_token="NEKOT")
        venue_of_validated_offerer = create_venue(offerer=offerer_validated, siret="12345678912345", name="B")
        venue_of_unvalidated_offerer = create_venue(offerer=offerer_not_validated, siret="98765432198765", name="A")

        repository.save(venue_of_validated_offerer, venue_of_unvalidated_offerer)

        expected_venue = venue_with_offerer_name_domain_converter.to_domain(venue_of_validated_offerer)

        # when
        found_venues = self.venue_sql_repository.get_by_pro_identifier(pro_user.id, False)

        # then
        assert len(found_venues) == 1
        assert found_venues[0].name == expected_venue.name

    @pytest.mark.usefixtures("db_session")
    def should_not_return_venues_of_non_validated_user_offerer(self, app: object):
        # given
        pro_user = create_user(email="john.doe@example.com")
        offerer = create_offerer(siren="123456789")
        create_user_offerer(user=pro_user, offerer=offerer, validation_token="NEKOT")
        venue = create_venue(offerer=offerer, siret="98765432198765", name="A")

        repository.save(venue)

        # when
        found_venues = self.venue_sql_repository.get_by_pro_identifier(pro_user.id, False)

        # then
        assert len(found_venues) == 0

    @pytest.mark.usefixtures("db_session")
    def should_return_venues_filtered_by_offerer_id_when_provided(self, app: object):
        # given
        pro_user = create_user()
        wanted_offerer = create_offerer(idx=1)
        unwanted_offerer = create_offerer(idx=2, siren="5654367")
        create_user_offerer(user=pro_user, offerer=wanted_offerer)
        create_user_offerer(user=pro_user, offerer=unwanted_offerer)
        venue_from_wanted_offerer = create_venue(
            name="Kléber", offerer=wanted_offerer, siret="12345678912345", public_name="Librairie Kléber"
        )
        venue_from_unwanted_offerer = create_venue(name="QG FNAC", offerer=unwanted_offerer, siret="98765432198765")

        repository.save(venue_from_wanted_offerer, venue_from_unwanted_offerer)

        # when
        found_venues = self.venue_sql_repository.get_by_pro_identifier(pro_user.id, False, Identifier(1))

        # then
        assert len(found_venues) == 1
        assert found_venues[0].name == venue_from_wanted_offerer.name
