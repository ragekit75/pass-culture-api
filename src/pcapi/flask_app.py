from datetime import datetime
import re
import typing

from flask import Blueprint
from flask import Flask
from flask import g
from flask import request
import flask.wrappers
from flask_admin import Admin
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
import redis
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.rq import RqIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from spectree import SpecTree
from sqlalchemy import orm
from werkzeug.middleware.profiler import ProfilerMiddleware

from pcapi import settings
from pcapi.models.db import db
from pcapi.serialization.utils import before_handler
from pcapi.utils.health_checker import read_version_from_file
from pcapi.utils.json_encoder import EnumJSONEncoder
from pcapi.utils.logger import json_logger


if settings.IS_DEV is False:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FlaskIntegration(), RedisIntegration(), RqIntegration(), SqlalchemyIntegration()],
        release=read_version_from_file(),
        environment=settings.ENV,
        traces_sample_rate=settings.SENTRY_SAMPLE_RATE,
    )

app = Flask(__name__, static_url_path="/static")

api = SpecTree("flask", MODE="strict", before=before_handler)
api.register(app)

login_manager = LoginManager()
admin = Admin(name="Back Office du Pass Culture", url="/pc/back-office/", template_mode="bootstrap3")

if settings.PROFILE_REQUESTS:
    profiling_restrictions = [settings.PROFILE_REQUESTS_LINES_LIMIT]
    app.config["PROFILE"] = True
    app.wsgi_app = ProfilerMiddleware(  # type: ignore
        app.wsgi_app,
        restrictions=profiling_restrictions,
    )

if not settings.JWT_SECRET_KEY:
    json_logger.error("JWT_SECRET_KEY not found in env")
    raise Exception("JWT_SECRET_KEY not found in env")

app.secret_key = settings.FLASK_SECRET
app.json_encoder = EnumJSONEncoder
app.config["SQLALCHEMY_DATABASE_URI"] = settings.DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = not settings.IS_DEV
# FIXME (cgaunet, 2021-01-27): this config has been modified to test
# gcp testing env before the whole migration is done
if settings.IS_TESTING:
    app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["REMEMBER_COOKIE_SECURE"] = not settings.IS_DEV
app.config["REMEMBER_COOKIE_DURATION"] = 90 * 24 * 3600
app.config["PERMANENT_SESSION_LIFETIME"] = 90 * 24 * 3600
app.config["FLASK_ADMIN_SWATCH"] = "flatly"
app.config["FLASK_ADMIN_FLUID_LAYOUT"] = True
app.config["JWT_SECRET_KEY"] = settings.JWT_SECRET_KEY

jwt = JWTManager(app)


@app.before_request
def before_request() -> None:
    g.start = datetime.utcnow()


@app.after_request
def log_request_details(response: flask.wrappers.Response) -> flask.wrappers.Response:
    request_duration = datetime.utcnow() - g.start
    request_duration_in_milliseconds = round(request_duration.total_seconds() * 1000, 2)
    request_data = {
        "statusCode": response.status_code,
        "method": request.method,
        "route": request.url_rule,
        "path": request.path,
        "queryParams": request.query_string.decode("UTF-8"),
        "duration": request_duration_in_milliseconds,
        "size": response.headers.get("Content-Length", type=int),
    }

    json_logger.info("request details", extra=request_data)

    return response


@app.after_request
def add_security_headers(response: flask.wrappers.Response) -> flask.wrappers.Response:
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "31536000; includeSubDomains; preload"

    return response


@app.teardown_request
def remove_db_session(
    exc: typing.Optional[Exception] = None,  # pylint: disable=unused-argument
) -> None:
    try:
        db.session.remove()
    except AttributeError:
        pass


admin.init_app(app)
db.init_app(app)
orm.configure_mappers()
login_manager.init_app(app)

public_api = Blueprint("Public API", __name__)
CORS(public_api, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

private_api = Blueprint("Private API", __name__)
CORS(
    private_api,
    resources={r"/*": {"origins": re.compile(settings.CORS_ALLOWED_ORIGIN)}},
    supports_credentials=True,
)

app.url_map.strict_slashes = False

with app.app_context():
    app.redis_client = redis.from_url(url=settings.REDIS_URL, decode_responses=True)
