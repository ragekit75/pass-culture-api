#!/usr/bin/env python
import os

from werkzeug.middleware.profiler import ProfilerMiddleware

from pcapi import settings
from pcapi.admin.install import install_admin_views
from pcapi.documentation import install_documentation
from pcapi.flask_app import admin
from pcapi.flask_app import app
from pcapi.flask_app import db
from pcapi.load_environment_variables import load_environment_variables
from pcapi.local_providers.install import install_local_providers
from pcapi.models.install import install_activity
from pcapi.models.install import install_features
from pcapi.models.install import install_materialized_views
from pcapi.repository.feature_queries import feature_request_profiling_enabled
from pcapi.routes import install_routes
from pcapi.routes.native.v1.blueprint import native_v1
from pcapi.utils.logger import configure_json_logger
from pcapi.utils.logger import disable_werkzeug_request_logs


configure_json_logger()
disable_werkzeug_request_logs()

if feature_request_profiling_enabled():
    profiling_restrictions = [int(os.environ.get("PROFILE_REQUESTS_LINES_LIMIT", 100))]
    app.config["PROFILE"] = True
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=profiling_restrictions)


def install_login_manager() -> None:
    # pylint: disable=unused-import
    import pcapi.utils.login_manager


with app.app_context():
    load_environment_variables()

    if settings.IS_DEV:
        install_activity()
        install_materialized_views()
        install_local_providers()
        install_features()

    install_login_manager()
    install_documentation()
    install_admin_views(admin, db.session)
    install_routes(app)

    app.register_blueprint(native_v1, url_prefix="/native/v1")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    import multiprocessing

    if multiprocessing.current_process().pid > 1:
        import debugpy

        if not debugpy.is_client_connected():
            debugpy.listen(("0.0.0.0", 10002))
            print("⏳ VS Code debugger can now be attached, press F5 in VS Code ⏳", flush=True)
            debugpy.wait_for_client()
            print("🎉 VS Code debugger attached, enjoy debugging 🎉", flush=True)

    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=True)
