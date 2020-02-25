import os
import subprocess
from io import StringIO

from apscheduler.schedulers.blocking import BlockingScheduler
from flask import Flask
from mailjet_rest import Client
from sqlalchemy import orm

from models import DiscoveryView
from models.db import db
from repository.feature_queries import feature_cron_send_final_booking_recaps_enabled, \
    feature_cron_generate_and_send_payments, \
    feature_cron_retrieve_offerers_bank_information, \
    feature_cron_send_remedial_emails, \
    feature_write_dashboard_enabled, \
    feature_update_booking_used, \
    feature_delete_all_unread_recommendations_older_than_one_week_enabled, \
    feature_cron_retrieve_bank_information_for_venue_without_siret, \
    feature_cron_send_wallet_balances, \
    feature_import_beneficiaries_enabled, \
    feature_cron_synchronize_allocine_stocks, \
    feature_update_recommendations_view, feature_cron_synchronize_libraires_stocks
from repository.provider_queries import get_provider_by_local_class
from repository.recommendation_queries import delete_useless_recommendations
from repository.user_queries import find_most_recent_beneficiary_creation_date
from scheduled_tasks.decorators import log_cron
from scripts.beneficiary import remote_import
from scripts.dashboard.write_dashboard import write_dashboard
from utils.config import API_ROOT_PATH
from utils.logger import logger
from utils.mailing import MAILJET_API_KEY, MAILJET_API_SECRET, parse_email_addresses

app = Flask(__name__, template_folder='../templates')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG'] = True
db.init_app(app)

RECO_VIEW_REFRESH_FREQUENCY = os.environ.get('RECO_VIEW_REFRESH_FREQUENCY', '*')


@log_cron
def pc_send_final_booking_recaps():
    with app.app_context():
        from scripts.send_final_booking_recaps import send_final_booking_recaps
        app.mailjet_client = Client(auth=(MAILJET_API_KEY, MAILJET_API_SECRET), version='v3')
        send_final_booking_recaps()


@log_cron
def pc_generate_and_send_payments(payment_message_id: str = None):
    with app.app_context():
        from scripts.payment.batch import generate_and_send_payments
        app.mailjet_client = Client(auth=(MAILJET_API_KEY, MAILJET_API_SECRET), version='v3')
        generate_and_send_payments(payment_message_id)


@log_cron
def pc_update_booking_used():
    with app.app_context():
        from scripts.update_booking_used import update_booking_used_after_stock_occurrence
        update_booking_used_after_stock_occurrence()


@log_cron
def pc_send_wallet_balances():
    with app.app_context():
        from scripts.payment.batch import send_wallet_balances
        app.mailjet_client = Client(auth=(MAILJET_API_KEY, MAILJET_API_SECRET), version='v3')
        recipients = parse_email_addresses(os.environ.get('WALLET_BALANCES_RECIPIENTS', None))
        send_wallet_balances(recipients)


@log_cron
def pc_synchronize_allocine_stocks():
    with app.app_context():
        allocine_stocks_provider_id = get_provider_by_local_class("AllocineStocks").id
        process = subprocess.Popen(
            f'PYTHONPATH="." python scripts/pc.py update_providables_by_provider_id'
            f' --provider-id {allocine_stocks_provider_id}',
            shell=True,
            cwd=API_ROOT_PATH)
        output, error = process.communicate()
        logger.info(StringIO(output))
        logger.info(StringIO(error))


@log_cron
def pc_synchronize_libraires_stocks():
    with app.app_context():
        libraires_stocks_provider_id = get_provider_by_local_class("LibrairesStocks").id
        process = subprocess.Popen(
            f'PYTHONPATH="." python scripts/pc.py update_providables_by_provider_id'
            f' --provider-id {libraires_stocks_provider_id}',
            shell=True,
            cwd=API_ROOT_PATH)
        output, error = process.communicate()
        logger.info(StringIO(output))
        logger.info(StringIO(error))


@log_cron
def pc_retrieve_offerers_bank_information():
    with app.app_context():
        process = subprocess.Popen('PYTHONPATH="." python scripts/pc.py update_providables'
                                   + ' --provider BankInformationProvider',
                                   shell=True,
                                   cwd=API_ROOT_PATH)
        output, error = process.communicate()
        logger.info(StringIO(output))
        logger.info(StringIO(error))


@log_cron
def pc_retrieve_bank_information_for_venue_without_siret():
    with app.app_context():
        process = subprocess.Popen('PYTHONPATH="." python scripts/pc.py update_providables'
                                   + ' --provider VenueWithoutSIRETBankInformationProvider',
                                   shell=True,
                                   cwd=API_ROOT_PATH)
        output, error = process.communicate()
        logger.info(StringIO(output))


@log_cron
def pc_send_remedial_emails():
    with app.app_context():
        from scripts.send_remedial_emails import send_remedial_emails
        app.mailjet_client = Client(auth=(MAILJET_API_KEY, MAILJET_API_SECRET), version='v3')
        send_remedial_emails()


@log_cron
def pc_remote_import_beneficiaries():
    with app.app_context():
        import_from_date = find_most_recent_beneficiary_creation_date()
        remote_import.run(import_from_date)


@log_cron
def pc_write_dashboard():
    with app.app_context():
        write_dashboard()


@log_cron
def pc_delete_useless_recommendations():
    with app.app_context():
        delete_useless_recommendations()


@log_cron
def pc_update_recommendations_view():
    with app.app_context():
        DiscoveryView.refresh()


if __name__ == '__main__':
    orm.configure_mappers()
    scheduler = BlockingScheduler()

    scheduler.add_job(pc_synchronize_libraires_stocks, 'cron', id='synchronize_libraire_stocks', day='*', hour='21')

    if feature_cron_send_final_booking_recaps_enabled():
        scheduler.add_job(pc_send_final_booking_recaps, 'cron', id='send_final_booking_recaps', day='*')

    if feature_cron_generate_and_send_payments():
        scheduler.add_job(pc_generate_and_send_payments, 'cron', id='generate_and_send_payments', day='1,15')

    if feature_cron_send_wallet_balances():
        scheduler.add_job(pc_send_wallet_balances, 'cron', id='send_wallet_balances', day='1-5')

    if feature_cron_retrieve_offerers_bank_information():
        scheduler.add_job(pc_retrieve_offerers_bank_information, 'cron', id='retrieve_offerers_bank_information',
                          day='*')

    if feature_cron_retrieve_bank_information_for_venue_without_siret():
        scheduler.add_job(pc_retrieve_bank_information_for_venue_without_siret, 'cron',
                          id='retrieve_bank_information_venue_without_siret',
                          day='*')

    if feature_cron_synchronize_allocine_stocks():
        scheduler.add_job(pc_synchronize_allocine_stocks, 'cron', id='synchronize_allocine_stocks',
                          day='*', hour='23')

    if feature_cron_synchronize_libraires_stocks():
        scheduler.add_job(pc_synchronize_libraires_stocks, 'cron', id='synchronize_libraires_stocks',
                          day='*', hour='22')

    if feature_cron_send_remedial_emails():
        scheduler.add_job(pc_send_remedial_emails, 'cron', id='send_remedial_emails', minute='*/15')

    if feature_import_beneficiaries_enabled():
        scheduler.add_job(pc_remote_import_beneficiaries, 'cron', id='remote_import_beneficiaries', day='*')

    if feature_write_dashboard_enabled():
        scheduler.add_job(pc_write_dashboard, 'cron', id='pc_write_dashboard', day='*', hour='4')

    if feature_update_booking_used():
        scheduler.add_job(pc_update_booking_used, 'cron', id='pc_update_booking_used', day='*', hour='0')

    if feature_delete_all_unread_recommendations_older_than_one_week_enabled():
        scheduler.add_job(pc_delete_useless_recommendations,
                          'cron',
                          id='pc_delete_useless_recommendations',
                          day_of_week='mon', hour='23')

    if feature_update_recommendations_view():
        scheduler.add_job(pc_update_recommendations_view, 'cron', id='pc_update_recommendations_view',
                          minute=RECO_VIEW_REFRESH_FREQUENCY)

    scheduler.start()