# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""
config.py
- settings for the flask application object
"""


import os
import redis
import random
import hashlib
from sweetrpg_assets_web.application import constants


def _env_bool(name: str, default: bool) -> bool:
    """Parse a boolean env var. `os.environ.get(name) or default` doesn't work for this - any
    non-empty string (including "false") is truthy, so that pattern always evaluates true once
    the var is set at all, regardless of its value.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _redis_url(db: int) -> str:
    host = os.environ[constants.REDIS_HOST]
    port = int(os.environ.get(constants.REDIS_PORT) or 6379)
    password = os.environ.get(constants.REDIS_PASS)
    auth = f":{password}@" if password else ""
    return f"redis://{auth}{host}:{port}/{db}"


class BaseConfig(object):
    DEBUG = _env_bool(constants.DEBUG, False)
    PORT = os.environ.get(constants.PORT) or 5000
    ASSETS_DEBUG = True
    LOG_LEVEL = os.environ.get(constants.LOG_LEVEL) or "INFO"
    # used for encryption and session management
    SECRET_KEY = os.environ.get("SECRET_KEY") or hashlib.sha256(f"{random.random()}".encode("utf-8")).hexdigest()
    CSRF_TOKEN = os.environ.get("CSRF_TOKEN") or hashlib.sha256(f"{random.random()}".encode("utf-8")).hexdigest()
    CACHE_REDIS_HOST = os.environ[constants.REDIS_HOST]
    CACHE_REDIS_PORT = int(os.environ.get(constants.REDIS_PORT) or 6379)
    CACHE_REDIS_DB = int(os.environ.get(constants.REDIS_DB) or 7)
    # None (not "") when unset, so redis-py skips the AUTH command entirely rather than sending
    # an empty password - the shared support cache doesn't have ACL auth enabled yet.
    CACHE_REDIS_PASSWORD = os.environ.get(constants.REDIS_PASS) or None
    SESSION_TYPE = "redis"
    SESSION_REDIS = redis.from_url(_redis_url(int(os.environ.get(constants.REDIS_DB) or 7)))
    SEGMENT_WRITE_KEY = os.environ.get(constants.SEGMENT_WRITE_KEY)

    # Asset storage
    ASSET_DATA_PATH = os.environ.get(constants.ASSET_DATA_PATH) or "/data"
    ASSET_CACHE_TTL = int(os.environ.get(constants.ASSET_CACHE_TTL) or 300)

    # Rate limiting - requests per minute, one shared process-wide bucket (matches the
    # platform's other services: a blunt backstop, not per-client throttling). Shares the same
    # Redis instance/db as the cache - flask-limiter's own key prefixes avoid collisions.
    RATE_LIMIT = os.environ.get(constants.RATE_LIMIT) or "120/minute"
    RATELIMIT_STORAGE_URI = _redis_url(int(os.environ.get(constants.REDIS_DB) or 7))

    # admin-api integration (banners, maintenance mode). Unset -> AdminClient runs disabled and
    # fails open (fetch_* always returns []), so leaving this unset is safe, not a startup error.
    ADMIN_API_URL = os.environ.get(constants.ADMIN_API_URL)

    # Suite-wide platform root (see docs/frontend-conventions.md in sweetrpg/platform) - defaults
    # to "/" so a local instance run standalone still links somewhere rather than to a broken URL.
    ROOT_URL = os.environ.get(constants.ROOT_URL) or "/"

    # shared-web base URL for branding assets (logo, favicon, stylesheet) - defaults to
    # shared-web's own local dev port so a standalone run still links somewhere real.
    SHARED_URL = os.environ.get(constants.SHARED_URL) or "http://localhost:8081"

    # Prefix this app is mounted under behind the reverse proxy (e.g. "/assets") - see
    # PrefixMiddleware in main.py. Empty/unset when run standalone (local dev, tests).
    APPLICATION_BASE_PATH = os.environ.get(constants.APPLICATION_BASE_PATH) or ""

    BUILD_INFO_PATH = os.environ.get(constants.BUILD_INFO_PATH) or "/app/build-info.json"

    # Shared suite-wide login session (see shared_session.py) - auth-web's own dedicated Redis
    # instance, distinct from CACHE_REDIS_* above. Unset SHARED_SESSION_REDIS_HOST ->
    # shared_session.current_user() fails open (every visitor reads as logged-out), matching
    # every other frontend's read-only shared-session client.
    SHARED_SESSION_REDIS_HOST = os.environ.get(constants.SHARED_SESSION_REDIS_HOST)
    SHARED_SESSION_REDIS_PORT = int(os.environ.get(constants.SHARED_SESSION_REDIS_PORT) or 6379)
    SHARED_SESSION_REDIS_DB = int(os.environ.get(constants.SHARED_SESSION_REDIS_DB) or 0)
    SHARED_SESSION_REDIS_PASSWORD = os.environ.get(constants.SHARED_SESSION_REDIS_PASS) or None

    # Auth0 tenant for validating forwarded user bearer tokens (see bearer_token.py) -
    # server-to-service calls (e.g. catalog-api promoting a staged cover) carry no browser
    # session cookie, so the token is their only authentication. Unset either value -> the
    # bearer path fails open as unauthenticated, matching shared_session's fail-open contract.
    AUTH0_DOMAIN = os.environ.get(constants.AUTH0_DOMAIN)
    AUTH0_AUDIENCE = os.environ.get(constants.AUTH0_AUDIENCE)

    # Staged-asset reclaim job (durable-volume-editing task 2.4). Unset EDIT_SESSION_REDIS_HOST
    # -> the reclaim endpoint 503s rather than guessing at a host, since silently skipping the
    # session check would mean deleting a still-in-use staged file.
    EDIT_SESSION_REDIS_HOST = os.environ.get(constants.EDIT_SESSION_REDIS_HOST)
    EDIT_SESSION_REDIS_PORT = int(os.environ.get(constants.EDIT_SESSION_REDIS_PORT) or 6379)
    EDIT_SESSION_REDIS_DB = int(os.environ.get(constants.EDIT_SESSION_REDIS_DB) or 2)
    CATALOG_API_URL = os.environ.get(constants.CATALOG_API_URL)
    RECLAIM_JOB_TOKEN = os.environ.get(constants.RECLAIM_JOB_TOKEN)
