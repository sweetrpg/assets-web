# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""main.py

Creates a Flask app instance and registers various services and middleware.
"""

from flask import Flask, session, g
from flask_cors import CORS
from flask_session import Session
from dotenv import load_dotenv, find_dotenv
from sweetrpg_assets_web.application.cache import cache
from sweetrpg_assets_web.application.limiter import create_limiter, FailOpenRedisStorage
from sweetrpg_assets_web.application.metrics import setup_metrics
from sweetrpg_assets_web.application.tracing import setup_tracing
from sweetrpg_assets_web.application import constants
from sweetrpg_assets_web.application.i18n import init_app as setup_i18n
from logging.config import dictConfig
from redis.client import Redis
from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware
from sweetrpg_admin_api_client import AdminClient
import analytics
import os

# Module-level limiter instance, initialized in create_app()
limiter = None


ENV_FILE = find_dotenv()
if ENV_FILE:
    print(f"Loading environment from {ENV_FILE}...")
    load_dotenv(ENV_FILE)


class PrefixMiddleware:
    """Injects APPLICATION_BASE_PATH into the WSGI environ's SCRIPT_NAME so url_for() generates
    links prefixed for the reverse proxy path this app is mounted under (e.g. "/assets").
    Traefik's strip-prefix Middleware already removes that prefix from PATH_INFO before the
    request reaches this app - uwsgi's --http mode builds environ purely from the incoming
    request, so without this, WSGI's SCRIPT_NAME is never populated and every generated URL
    comes out unprefixed, pointing at a path this app's Ingress doesn't own.
    """

    def __init__(self, app, prefix=""):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        if self.prefix:
            environ["SCRIPT_NAME"] = self.prefix
            path_info = environ.get("PATH_INFO", "")
            if path_info.startswith(self.prefix):
                environ["PATH_INFO"] = path_info[len(self.prefix):]
        return self.app(environ, start_response)


def create_app(app_name=constants.APPLICATION_NAME):
    print("Configuring logging...")
    dictConfig(
        {
            "version": 1,
            "formatters": {
                # One JSON object per line to stdout - matches the Go/Swift services'
                # structured-logging convention so log aggregation parses all of them the same
                # way.
                "json": {
                    "class": "pythonjsonlogger.json.JsonFormatter",
                    "format": "%(asctime)s %(levelname)s %(module)s %(funcName)s %(message)s",
                },
            },
            "handlers": {
                "wsgi": {"class": "logging.StreamHandler", "stream": "ext://flask.logging.wsgi_errors_stream", "formatter": "json"},
            },
            "root": {
                "level": os.environ.get(constants.LOG_LEVEL) or "INFO",
                "handlers": [
                    "wsgi",
                ],
            },
        }
    )

    # static_folder=None: app_name isn't a real module name, so Flask's default static_folder
    # would resolve relative to the process's cwd rather than this package - the shared static
    # route in blueprints/__init__.py serves its own directory from an absolute, __file__-derived
    # path instead of relying on that.
    app = Flask(app_name, static_folder=None)
    # Load config before touching app.debug - it must reflect BaseConfig.DEBUG, not Flask's
    # own pre-config default, or the Sentry setup below (`if not app.debug`) checks a value
    # that was never actually set from the environment.
    app.config.from_object("sweetrpg_assets_web.application.config.BaseConfig")

    app.logger.info("Setting up cache...")
    cache.init_app(app)

    app.logger.info("Setting up rate limiter...")
    app.config["RATELIMIT_DEFAULT"] = app.config["RATE_LIMIT"]
    # Create limiter with fail-open Redis storage wrapper
    global limiter
    limiter = create_limiter(app.config["RATELIMIT_STORAGE_URI"])
    limiter.init_app(app)

    app.logger.info("Setting up metrics...")
    setup_i18n(app)

    setup_metrics(app)

    app.logger.info("Setting up tracing...")
    setup_tracing(app)

    app.logger.info("Setting up analytics...")
    analytics.write_key = app.config.get(constants.SEGMENT_WRITE_KEY)
    analytics.debug = app.config.get(constants.DEBUG, False)

    app.logger.info("Setting up session manager...")
    session = Session(app)

    # One client for the process lifetime, same pattern as `cache`/`limiter` above - the SDK
    # bakes in its own TTL cache, timeout, and fail-open behavior (returns [] rather than
    # raising if ADMIN_API_URL is unset or admin-api is unreachable), so an unconfigured or down
    # admin-api never breaks this app's own rendering.
    app.admin_client = AdminClient(base_url=app.config.get("ADMIN_API_URL"))

    cors = CORS(app, resources={r"/*": {"origins": "*"}})

    if not app.debug:
        app.logger.info("Setting up Sentry...")
        sentry = SentryWsgiMiddleware(app)

    app.logger.info("Setting up endpoints...")

    from sweetrpg_assets_web.application.blueprints import blueprint as main_blueprint

    from sweetrpg_web_core.blueprints.health import blueprint as health_blueprint

    # main_blueprint is a module-level singleton, so registering health_blueprint onto it is a
    # one-time setup step, not per-app-instance - Flask rejects registering the same Blueprint
    # object twice. Only relevant when create_app() runs more than once in a process (tests,
    # a REPL); each real worker process calls it exactly once.
    if not main_blueprint._got_registered_once:
        main_blueprint.register_blueprint(health_blueprint)

    app.register_blueprint(main_blueprint)

    # Exempt /health/ping from rate limiting - it's a simple liveness probe that must
    # remain reachable even when Redis is down. /health/status should NOT be exempt;
    # it checks dependencies (including Redis) and should be rate-limited.
    with app.app_context():
        if "web.health.ping" in app.view_functions:
            limiter.exempt(app.view_functions["web.health.ping"])

    # Register Redis health check for /health/status
    from sweetrpg_web_core.blueprints.health import register_health_check_service_hook

    def _redis_health():
        try:
            cache.get("__health_check__")
            return "healthy"
        except Exception:
            return "degraded"

    register_health_check_service_hook("redis", _redis_health)

    app.wsgi_app = PrefixMiddleware(app.wsgi_app, app.config.get("APPLICATION_BASE_PATH", ""))

    print(app.url_map)

    return app
