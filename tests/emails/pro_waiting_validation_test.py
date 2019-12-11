from unittest.mock import patch

from emails.pro_waiting_validation import retrieve_data_for_pro_user_waiting_offerer_validation_email
from tests.test_utils import create_user, create_offerer


class MakeProUserWaitingForValidationByAdminEmailTest:
    @patch('emails.pro_waiting_validation.SUPPORT_EMAIL_ADDRESS', 'support@example.com')
    @patch('emails.pro_waiting_validation.DEV_EMAIL_ADDRESS', 'dev@example.com')
    def test_should_return_mailjet_data_with_dev_email_when_not_in_production(self):
        # Given
        user = create_user()
        user.generate_validation_token()
        offerer = create_offerer(name='Bar des amis')

        # When
        mailjet_data = retrieve_data_for_pro_user_waiting_offerer_validation_email(user, offerer)

        # Then
        assert mailjet_data == {
            'FromEmail': 'support@example.com',
            'MJ-TemplateID': 778329,
            'MJ-TemplateLanguage': True,
            'To': 'dev@example.com',
            'Vars':
                {
                    'nom_structure': 'Bar des amis'
                }
        }

    @patch('emails.pro_waiting_validation.SUPPORT_EMAIL_ADDRESS', 'support@example.com')
    @patch('emails.pro_waiting_validation.feature_send_mail_to_users_enabled', return_value=True)
    def test_should_return_mailjet_data_with_user_email_when_in_production(self,
                                                                           mock_feature_send_mail_to_users_enabled):
        # Given
        user = create_user(email='user@example.com')
        user.generate_validation_token()
        offerer = create_offerer(name='Bar des amis')

        # When
        mailjet_data = retrieve_data_for_pro_user_waiting_offerer_validation_email(user, offerer)

        # Then
        assert mailjet_data == {
            'FromEmail': 'support@example.com',
            'MJ-TemplateID': 778329,
            'MJ-TemplateLanguage': True,
            'To': 'user@example.com',
            'Vars':
                {
                    'nom_structure': 'Bar des amis'
                }
        }