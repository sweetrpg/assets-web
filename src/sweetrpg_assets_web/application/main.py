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
from sweetrpg_assets_web.application.limiter import limiter
from sweetrpg_assets_web.application.metrics import setup_metrics
from sweetrpg_assets_web.application.tracing import setup_tracing
from sweetrpg_assets_web.application import constants
from logging.config import dictConfig
from redis.client import Redis
from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware
import analytics
import os


ENV_FILE = find_dotenv()
if ENV_FILE:
    print(f"Loading environment from {ENV_FILE}...")
    load_dotenv(ENV_FILE)


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
    limiter.init_app(app)

    app.logger.info("Setting up metrics...")
    setup_metrics(app)

    app.logger.info("Setting up tracing...")
    setup_tracing(app)

    app.logger.info("Setting up analytics...")
    analytics.write_key = app.config.get(constants.SEGMENT_WRITE_KEY)
    analytics.debug = app.config.get(constants.DEBUG, False)

    app.logger.info("Setting up session manager...")
    session = Session(app)

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

    print(app.url_map)

    return app
