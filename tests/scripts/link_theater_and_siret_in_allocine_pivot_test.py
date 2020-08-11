from models import AllocinePivot
from repository import repository
from scripts.link_theater_and_siret_in_allocine_pivot import link_theater_to_siret
from tests.conftest import clean_database
from tests.model_creators.generic_creators import create_venue, create_offerer


@clean_database
def should_create_link_between_siret_and_theater(app):
    # Given
    offerer = create_offerer()
    venue = create_venue(offerer)
    repository.save(venue)
    theater_id = 'XXXXXXXXXXXXXXXXXX=='

    # When
    link_theater_to_siret(venue.siret, theater_id)

    # Then
    assert AllocinePivot.query.filter_by(siret=venue.siret, theaterId=theater_id).one() is not None