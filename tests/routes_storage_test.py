import pytest

from models import PcObject
from tests.conftest import clean_database
from utils.human_ids import humanize
from utils.test_utils import API_URL, create_venue, create_offerer, create_user, req_with_auth, ONE_PIXEL_PNG


@clean_database
@pytest.mark.standalone
def test_post_storage_file_returns_bad_request_if_upload_is_not_authorized_on_model(app):
    # given
    user = create_user(password='p@55sw0rd')
    offerer = create_offerer()
    venue = create_venue(offerer)
    PcObject.check_and_save(user, venue, offerer)

    auth_request = req_with_auth(email=user.email, password='p@55sw0rd')

    # when
    response = auth_request.post(
        API_URL + '/storage/thumb/%s/%s/%s' % ('venues', humanize(venue.id), '1'),
        data={},
        files={'file': ('1.png', b'123')}
    )

    # then
    assert response.status_code == 400
    assert response.json()['text'] == 'upload is not authorized for this model'


@clean_database
@pytest.mark.standalone
def test_post_storage_file_update_a_thumb_for_an_user(app):
    # given
    user = create_user(password='p@55sw0rd')
    offerer = create_offerer()
    venue = create_venue(offerer)
    PcObject.check_and_save(user, venue, offerer)

    auth_request = req_with_auth(email=user.email, password='p@55sw0rd')

    # when
    response = auth_request.post(
        API_URL + '/storage/thumb/%s/%s/%s' % ('users', humanize(user.id), '0'),
        data={},
        files={'file': ('1.png', ONE_PIXEL_PNG)}
    )

    # then
    assert response.status_code == 200
