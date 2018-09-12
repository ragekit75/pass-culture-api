""" user mediations routes """
import csv
import os
from datetime import datetime
from inspect import isclass
from io import BytesIO, StringIO

from flask import current_app as app, jsonify, request, send_file
from postgresql_audit.flask import versioning_manager
from sqlalchemy import func

import models
from models import Booking
from models import Event
from models import EventOccurrence
from models import Offer
from models import Offerer
from models import Recommendation
from models import Stock
from models import Thing
from models import User
from models import UserOfferer
from models import Venue
from models.api_errors import ApiErrors
from models.db import db
from models.pc_object import PcObject
from repository.booking_queries import find_bookings_stats_per_department
from repository.user_queries import find_users_by_department_and_date_range, find_users_stats_per_department

Activity = versioning_manager.activity_cls

EXPORT_TOKEN = os.environ.get('EXPORT_TOKEN')


@app.route('/exports/models', methods=['GET'])
def list_export_urls():
    _check_token()
    return "\n".join([request.host_url + 'exports/models/' + model_name
                      + '?token=' + request.args.get('token')
                      for model_name in filter(_is_exportable, models.__all__)])


@app.route('/exports/models/<model_name>', methods=['GET'])
def export_table(model_name):
    _check_token()
    ae = ApiErrors()
    if model_name not in models.__all__:
        ae.addError('global', 'Classe inconnue : ' + model_name)
        return jsonify(ae.errors), 400

    try:
        model = getattr(models, model_name)
    except KeyError:
        ae.addError('global', 'Nom de classe incorrect : ' + model_name)
        return jsonify(ae.errors), 400

    if not _is_exportable(model_name):
        ae.addError('global', 'Classe non exportable : ' + model_name)
        return jsonify(ae.errors), 400

    objects = model.query.all()

    if len(objects) == 0:
        return "", 200

    csvfile = StringIO()
    header = _clean_dict_for_export(model_name, objects[0]._asdict()).keys()
    if model_name == 'User':
        header = list(filter(lambda h: h != 'id' and h != 'password', header))
    writer = csv.DictWriter(csvfile, header, extrasaction='ignore')
    writer.writeheader()
    for obj in objects:
        dct = _clean_dict_for_export(model_name, obj._asdict())
        writer.writerow(dct)
    csvfile.seek(0)
    mem = BytesIO()
    mem.write(csvfile.getvalue().encode('utf-8'))
    mem.seek(0)
    csvfile.close()
    return send_file(mem,
                     attachment_filename='export.csv',
                     as_attachment=True)


@app.route('/exports/users', methods=['GET'])
def get_users_per_date_per_department():
    _check_token()
    date_min = request.args.get('date_min')
    date_max = request.args.get('date_max')
    department = request.args.get('department')

    users = find_users_by_department_and_date_range(date_max, date_min, department)
    file_name = 'export_%s_users.csv' % datetime.utcnow().strftime('%y_%m_%d')
    headers = ['user_id', 'dateCreated', 'department']
    return _make_csv_response(file_name, headers, users)


@app.route('/exports/users_stats', methods=['GET'])
def get_users_stats():
    _check_token()
    date_intervall = valid_time_intervall_or_default(request.args.get('type_date'))

    users_stats = find_users_stats_per_department(date_intervall)

    file_name = 'export_%s_users_stats.csv' % datetime.utcnow().strftime('%y_%m_%d')
    headers = ['department', 'date_intervall', 'distinct_user']
    return _make_csv_response(file_name, headers, users_stats)


@app.route('/exports/bookings_stats', methods=['GET'])
def get_bookings_stats():
    _check_token()
    date_intervall = valid_time_intervall_or_default(request.args.get('type_date'))

    bookings_stats = find_bookings_stats_per_department(date_intervall)

    file_name = 'export_%s_users_stats.csv' % datetime.utcnow().strftime('%y_%m_%d')
    headers = ['department', 'date_intervall', 'bookings_per_venue_dpt', 'bookings_per_user_dpt', 'distinct_user']
    return _make_csv_response(file_name, headers, bookings_stats)


@app.route('/exports/bookings', methods=['GET'])
def get_bookings_per_date_per_departement():
    _check_token()
    booking_date_min = request.args.get('booking_date_min')
    booking_date_max = request.args.get('booking_date_max')
    event_date_min = request.args.get('event_date_min')
    event_date_max = request.args.get('event_date_max')
    user_department = request.args.get('user_department')
    venue_department = request.args.get('venue_department')

    query = db.session.query(User.id, User.departementCode, Booking.id, Activity.issued_at, EventOccurrence.id, EventOccurrence.beginningDatetime, Venue.departementCode, Offerer.id, Offerer.name, Event.id, Event.name, Activity.id) \
        .join(Booking) \
        .join(Activity, Activity.table_name == 'booking') \
        .filter(Activity.verb == 'insert', Activity.data['id'].astext.cast(db.Integer) == Booking.id) \
        .join(Stock) \
        .join(EventOccurrence) \
        .join(Offer) \
        .join(Venue) \
        .join(Offerer) \
        .join(Event)

    if booking_date_min:
        query = query.filter(Activity.issued_at >= booking_date_min)
    if booking_date_max:
        query = query.filter(Activity.issued_at <=  booking_date_max)
    if event_date_min:
        query = query.filter(EventOccurrence.beginningDatetime >= event_date_min)
    if event_date_max:
        query = query.filter(EventOccurrence.beginningDatetime <= event_date_max)
    if user_department:
        query = query.filter(User.departementCode == user_department)
    if venue_department:
        query = query.filter(Venue.departementCode == venue_department)

    result = query.group_by(Booking.id, User.id, Activity.issued_at, EventOccurrence.id, EventOccurrence.beginningDatetime, Venue.departementCode, Offerer.id, Offerer.name, Event.id, Event.name, Activity.id).order_by(Booking.id, Activity.issued_at).all()
    file_name = 'export_%s_bookings.csv' % datetime.utcnow().strftime('%y_%m_%d')
    headers = ['User_id', 'User_departementCode', 'Booking_id', 'Booking_issued_at', 'EventOccurrence_id', 'EventOccurrence_beginningDatetime', 'Venue_departementCode', 'Offerer_id', 'Offerer_name', 'Event_id', 'Event_name', 'Activity_id']
    return _make_csv_response(file_name, headers, result)


@app.route('/exports/offers', methods=['GET'])
def get_offers_per_date_per_department():
    _check_token()
    date_min = request.args.get('date_min')
    date_max = request.args.get('date_max')
    department = request.args.get('department')

    query = db.session.query(Offer.id, Event.id, Event.name, EventOccurrence.beginningDatetime, Venue.departementCode, Offerer.id, Offerer.name) \
        .join(Event) \
        .join(EventOccurrence) \
        .join(Venue) \
        .join(Offerer)

    if department:
        query = query.filter(Venue.departementCode == department)
    if date_min:
        query = query.filter(EventOccurrence.beginningDatetime >= date_min)
    if date_max:
        query = query.filter(EventOccurrence.beginningDatetime <= date_max)

    result = query.order_by(EventOccurrence.beginningDatetime) \
        .all()
    file_name = 'export_%s_offers.csv' % datetime.utcnow().strftime('%y_%m_%d')
    headers = ['offer_id', 'event_id', 'event_name', 'event_date', 'departement_code', 'Offerer_id', 'Offerer_name']
    return _make_csv_response(file_name, headers, result)


@app.route('/exports/offerers', methods=['GET'])
def get_offerers_per_date_per_departement():
    _check_token()
    date_min = request.args.get('date_min')
    date_max = request.args.get('date_max')
    department = request.args.get('department')

    query = db.session.query(func.distinct(Offerer.id), Offerer.name, Activity.issued_at, Venue.departementCode) \
        .join(Venue) \
        .join(Activity, Activity.table_name == 'offerer') \
        .filter(Activity.verb == 'insert', Activity.data['id'].astext.cast(db.Integer) == Offerer.id)

    if department:
        query = query.filter(Venue.departementCode == department)
    if date_min:
        query = query.filter(Activity.issued_at >= date_min)
    if date_max:
        query = query.filter(Activity.issued_at <= date_max)

    result = query.order_by(Activity.issued_at) \
        .all()

    file_name = 'export_%s_offerers.csv' % datetime.utcnow().strftime('%y_%m_%d')
    headers = ['Offerer_id', 'Offerer_name', 'dateCreated', 'departement_code']
    return _make_csv_response(file_name, headers, result)


@app.route('/exports/venue_per_department', methods=['GET'])
def get_venue_per_department():
    _check_token()

    result = db.session.query(Venue.departementCode, func.count(Venue.id)) \
        .group_by(Venue.departementCode) \
        .order_by(Venue.departementCode) \
        .all()

    file_name = 'export_%s_venue_per_department.csv' % datetime.utcnow().strftime('%y_%m_%d')
    headers = ['departement_code', 'nb_Venue']
    return _make_csv_response(file_name, headers, result)


@app.route('/exports/tracked_activity', methods=['GET'])
def get_tracked_activity_from_id():
    _check_token()
    object_id = _check_int(request.args.get('object_id'))
    table_name = request.args.get('table_name')

    result = db.session.query(Activity.id, Activity.verb, Activity.issued_at, Activity.changed_data) \
        .filter(Activity.table_name == table_name, 
        Activity.data['id'].astext.cast(db.Integer) == object_id) \
        .all()

    file_name = 'export_%s_tracked_activity.csv' % datetime.utcnow().strftime('%y_%m_%d')
    headers = []
    return _make_csv_response(file_name, headers, result)


@app.route('/exports/offerers_users_offers_bookings', methods=['GET'])
def get_offerers_users_offers_bookings():
    _check_token()
    department = request.args.get('department')

    query = db.session.query(Offerer.name, UserOfferer.id, User.email, User.dateCreated, Venue.departementCode, Offer.dateCreated, Event.name, Activity.issued_at, Booking.dateModified) \
        .join(Venue) \
        .outerjoin(Offer) \
        .outerjoin(EventOccurrence)\
        .join(Stock)\
        .outerjoin(Booking) \
        .join(Event) \
        .outerjoin(UserOfferer) \
        .outerjoin (User) \
        .join(Activity, Activity.table_name == 'event') \
        .filter(Activity.verb == 'insert', Activity.data['id'].astext.cast(db.Integer) == Event.id)

    if department:
        query = query.filter(Venue.departementCode == department)

    result = query.order_by(Offerer.id).all()
    file_name = 'export_%s_offerers_users_offers_bookings.csv' % datetime.utcnow().strftime('%y_%m_%d')
    headers = ['Offerer_name', 'UserOfferer_id', 'User_email', 'User_dateCreated', 'Venue_departementCode', 'Offer_dateCreated', 'Event_name', 'Activity_issued_at', 'Booking_dateModified']
    return _make_csv_response(file_name, headers, result)


@app.route('/exports/recommendations', methods=['GET'])
def get_recommendations():
    _check_token()
    department = request.args.get('department')
    date_min = request.args.get('date_min')
    date_max = request.args.get('date_max')

    query = db.session.query(Offer.id, Event.name, Thing.name, func.count(Offer.id), Venue.departementCode, Recommendation.isClicked, Recommendation.isFavorite) \
        .join(Recommendation) \
        .outerjoin(Event) \
        .outerjoin(Thing) \
        .join(Venue) \

    if department:
        query = query.filter(Venue.departementCode == department)
    if date_min:
        query = query.filter(Recommendation.dateCreated >= date_min)
    if date_max:
        query = query.filter(Recommendation.dateCreated <= date_max)

    result = query.group_by(Offer.id, Event.name, Thing.name, Venue.departementCode, Recommendation.isClicked, Recommendation.isFavorite).order_by(Offer.id).all()
    file_name = 'export_%s_recommendations.csv' % datetime.utcnow().strftime('%y_%m_%d')
    headers = ['Offer_id', 'Event_name', 'Thing_name', 'countOffer_id', 'Venue_departementCode', 'Recommendation_isClicked', 'Recommendation_isFavorite']
    return _make_csv_response(file_name, headers, result)


def _make_csv_response(file_name, headers, result):
    csv_file = StringIO()
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(headers)
    csv_writer.writerows(result)
    csv_file.seek(0)
    mem = BytesIO()
    mem.write(csv_file.getvalue().encode('utf-8'))
    mem.seek(0)
    csv_file.close()
    return send_file(mem, attachment_filename=file_name, as_attachment=True)


def _check_token():
    if EXPORT_TOKEN is None or EXPORT_TOKEN == '':
        raise ValueError("Missing environment variable EXPORT_TOKEN")
    token = request.args.get('token')
    api_errors = ApiErrors()
    if token is None:
        api_errors.addError('token', 'Vous devez préciser un jeton dans l''adresse (token=XXX)')
    if not token == EXPORT_TOKEN:
        api_errors.addError('token', 'Le jeton est invalide')
    if api_errors.errors:
        raise api_errors


def _is_exportable(model_name):
    model = getattr(models, model_name)
    return not model_name == 'PcObject' \
           and isclass(model) \
           and issubclass(model, PcObject)


def _clean_dict_for_export(model_name, dct):
    if model_name == 'User':
        del (dct['password'])
        del (dct['id'])
    return dct


def valid_time_intervall_or_default(time_intervall):
    if time_intervall == 'year' or time_intervall == 'month' or time_intervall == 'week' or time_intervall == 'day':
        return time_intervall
    return 'day'


def _check_int(checked_int):
    try: 
        int(checked_int)
        return checked_int
    except:
        return 0