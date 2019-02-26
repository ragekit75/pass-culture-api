import pytest
import secrets

from models import PcObject
from tests.conftest import clean_database, TestClient
from tests.test_utils import API_URL, \
    create_offerer, \
    create_user, \
    create_user_offerer, \
    req_with_auth, create_bank_information


@pytest.mark.standalone
class Get:
    class Returns401:
        @clean_database
        def when_user_is_not_logged_in(self, app):
            # when
            response = TestClient().get(API_URL + '/offerers', headers={'origin': 'http://localhost:3000'})

            # then
            assert response.status_code == 401

    class Returns200:
        @clean_database
        def when_logged_in_and_return_a_list_of_offerers_sorted_alphabetically(self, app):
            # given
            offerer1 = create_offerer(siren='123456781', name='offreur C')
            offerer2 = create_offerer(siren='123456782', name='offreur A')
            offerer3 = create_offerer(siren='123456783', name='offreur B')
            PcObject.check_and_save(offerer1, offerer3, offerer2)

            user = create_user(password='p@55sw0rd')
            user.offerers = [offerer1, offerer2, offerer3]
            PcObject.check_and_save(user)

            # when
            response = TestClient() \
                .with_auth(user.email, user.clearTextPassword) \
                .get(API_URL + '/offerers')

            # then
            assert response.status_code == 200
            offerers = response.json()
            assert len(offerers) == 3
            names = [offerer['name'] for offerer in offerers]
            assert names == ['offreur A', 'offreur B', 'offreur C']

        @clean_database
        def when_current_user_is_not_admin_and_returns_only_offers_managed_by_him(self, app):
            # given
            offerer1 = create_offerer(siren='123456781', name='offreur C')
            offerer2 = create_offerer(siren='123456782', name='offreur A')
            offerer3 = create_offerer(siren='123456783', name='offreur B')
            PcObject.check_and_save(offerer1, offerer3, offerer2)

            user = create_user(can_book_free_offers=True, password='p@55sw0rd', is_admin=False)
            user.offerers = [offerer1, offerer2]
            PcObject.check_and_save(user)

            # when
            response = TestClient() \
                .with_auth(user.email, user.clearTextPassword) \
                .get(API_URL + '/offerers')

            # then
            assert response.status_code == 200
            assert len(response.json()) == 2

        @clean_database
        def when_current_user_is_admin_and_returns_all_offerers(self, app):
            # given
            offerer1 = create_offerer(siren='123456781', name='offreur C')
            offerer2 = create_offerer(siren='123456782', name='offreur A')
            offerer3 = create_offerer(siren='123456783', name='offreur B')
            PcObject.check_and_save(offerer1, offerer3, offerer2)

            user = create_user(can_book_free_offers=False, password='p@55sw0rd', is_admin=True)
            user.offerers = [offerer1, offerer2]
            PcObject.check_and_save(user)

            # when
            response = TestClient() \
                .with_auth(user.email, user.clearTextPassword) \
                .get(API_URL + '/offerers')

            # then
            assert response.status_code == 200
            assert len(response.json()) == 3

        @clean_database
        def when_user_is_admin_and_param_validated_is_false_and_returns_all_info_of_all_offerers(
                self, app):
            # given
            offerer1 = create_offerer(siren='123456781', name='offreur C')
            offerer2 = create_offerer(siren='123456782', name='offreur A')
            offerer3 = create_offerer(siren='123456783', name='offreur B')
            PcObject.check_and_save(offerer1, offerer3, offerer2)
            bank_information1 = create_bank_information(offerer_id=offerer1.id, id_at_providers='123456781')
            bank_information2 = create_bank_information(offerer_id=offerer2.id, id_at_providers='123456782')
            bank_information3 = create_bank_information(offerer_id=offerer3.id, id_at_providers='123456783')

            user = create_user(can_book_free_offers=False, password='p@55sw0rd', is_admin=True)
            user.offerers = [offerer1, offerer2]
            PcObject.check_and_save(user, bank_information1, bank_information2, bank_information3)

            # when
            response = TestClient() \
                .with_auth(user.email, user.clearTextPassword) \
                .get(API_URL + '/offerers?validated=false')

            # then
            assert response.status_code == 200
            assert set(response.json()[0].keys()) == {
                'address', 'bic', 'city', 'dateCreated', 'dateModifiedAtLastProvider',
                'firstThumbDominantColor', 'iban', 'id', 'idAtProviders', 'isActive',
                'isValidated', 'lastProviderId', 'managedVenues', 'modelName', 'nOffers',
                'name', 'postalCode', 'siren', 'thumbCount'
            }

        @clean_database
        def when_param_validated_is_false_and_returns_only_not_validated_offerers(self, app):
            # given
            user = create_user(password='p@55sw0rd')
            offerer1 = create_offerer(siren='123456781', name='offreur C')
            offerer2 = create_offerer(siren='123456782', name='offreur A')
            offerer3 = create_offerer(siren='123456783', name='offreur B')
            user_offerer1 = create_user_offerer(user, offerer1, validation_token=None)
            user_offerer2 = create_user_offerer(user, offerer2, validation_token='AZE123')
            user_offerer3 = create_user_offerer(user, offerer3, validation_token=None)
            PcObject.check_and_save(user_offerer1, user_offerer2, user_offerer3)

            # when
            response = TestClient() \
                .with_auth(user.email, user.clearTextPassword) \
                .get(API_URL + '/offerers?validated=false')

            # then
            assert response.status_code == 200
            assert len(response.json()) == 1

        @clean_database
        def when_param_validated_is_false_and_returns_only_name_and_siren_of_not_validated_offerers(
                self, app):
            # given
            user = create_user(password='p@55sw0rd')
            offerer1 = create_offerer(siren='123456781', name='offreur C')
            offerer2 = create_offerer(siren='123456782', name='offreur A')
            offerer3 = create_offerer(siren='123456783', name='offreur B')
            user_offerer1 = create_user_offerer(user, offerer1, validation_token=None)
            user_offerer2 = create_user_offerer(user, offerer2, validation_token='AZE123')
            user_offerer3 = create_user_offerer(user, offerer3, validation_token=None)
            PcObject.check_and_save(user_offerer1, user_offerer2, user_offerer3)

            # when
            response = TestClient() \
                .with_auth(user.email, user.clearTextPassword) \
                .get(API_URL + '/offerers?validated=false')

            # then
            assert response.status_code == 200
            assert len(response.json()) == 1
            assert response.json()[0] == {'modelName': 'Offerer', 'name': 'offreur A', 'siren': '123456782'}

        @clean_database
        def when_param_validated_is_true_and_returns_only_validated_offerers_if(self, app):
            # given
            user = create_user(password='p@55sw0rd')
            offerer1 = create_offerer(siren='123456781', name='offreur C')
            offerer2 = create_offerer(siren='123456782', name='offreur A')
            offerer3 = create_offerer(siren='123456783', name='offreur B')
            user_offerer1 = create_user_offerer(user, offerer1, validation_token=None)
            user_offerer2 = create_user_offerer(user, offerer2, validation_token='AZE123')
            user_offerer3 = create_user_offerer(user, offerer3, validation_token=None)
            PcObject.check_and_save(user_offerer1, user_offerer2, user_offerer3)

            # when
            response = TestClient() \
                .with_auth(user.email, user.clearTextPassword) \
                .get(API_URL + '/offerers?validated=true')

            # then
            assert response.status_code == 200
            assert len(response.json()) == 2
            assert response.json()[0]['name'] == 'offreur B'
            assert response.json()[1]['name'] == 'offreur C'

        @clean_database
        def when_param_validated_is_true_returns_all_info_of_validated_offerers(self, app):
            # given
            user = create_user(password='p@55sw0rd')
            offerer1 = create_offerer(siren='123456781', name='offreur C')
            offerer2 = create_offerer(siren='123456782', name='offreur A')
            offerer3 = create_offerer(siren='123456783', name='offreur B')
            user_offerer1 = create_user_offerer(user, offerer1, validation_token=None)
            user_offerer2 = create_user_offerer(user, offerer2, validation_token='AZE123')
            user_offerer3 = create_user_offerer(user, offerer3, validation_token=None)
            PcObject.check_and_save(user_offerer1, user_offerer2, user_offerer3)
            bank_information1 = create_bank_information(offerer_id=offerer1.id, id_at_providers='123456781')
            bank_information2 = create_bank_information(offerer_id=offerer2.id, id_at_providers='123456782')
            bank_information3 = create_bank_information(offerer_id=offerer3.id, id_at_providers='123456783')
            PcObject.check_and_save(bank_information1, bank_information2, bank_information3)

            # when
            response = TestClient() \
                .with_auth(user.email, user.clearTextPassword) \
                .get(API_URL + '/offerers?validated=true')

            # then
            assert response.status_code == 200
            assert len(response.json()) == 2
            assert list(response.json()[0].keys()) == [
                'address', 'bic', 'city', 'dateCreated', 'dateModifiedAtLastProvider',
                'firstThumbDominantColor', 'iban', 'id', 'idAtProviders', 'isActive',
                'isValidated', 'lastProviderId', 'managedVenues', 'modelName', 'nOffers',
                'name', 'postalCode', 'siren', 'thumbCount'
            ]

        @clean_database
        @pytest.mark.standalone
        def when_user_offerer_is_not_validated_but_returns_no_offerer(self, app):
            # Given
            offerer = create_offerer()
            user = create_user(password='p@55sw0rd!')
            user_offerer = create_user_offerer(user, offerer, validation_token=secrets.token_urlsafe(20))
            PcObject.check_and_save(user_offerer)
            auth_request = req_with_auth(email=user.email, password='p@55sw0rd!')

            # When
            response = auth_request.get(API_URL + '/offerers/')

            # then
            assert response.status_code == 200
            assert response.json() == []

    class Returns400:
        @clean_database
        def when_param_validated_is_not_true_nor_false(self, app):
            # given
            offerer1 = create_offerer(siren='123456781', name='offreur C')
            offerer2 = create_offerer(siren='123456782', name='offreur A')
            offerer3 = create_offerer(siren='123456783', name='offreur B')
            PcObject.check_and_save(offerer1, offerer3, offerer2)

            user = create_user(can_book_free_offers=False, password='p@55sw0rd', is_admin=True)
            user.offerers = [offerer1, offerer2]
            PcObject.check_and_save(user)

            # when
            response = TestClient() \
                .with_auth(user.email, user.clearTextPassword) \
                .get(API_URL + '/offerers?validated=blabla')

            # then
            assert response.status_code == 400
            assert response.json()['validated'] == ["Le paramètre 'validated' doit être 'true' ou 'false'"]
