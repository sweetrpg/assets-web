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
    SWEETRPG_ROOT_URL = os.environ.get(constants.SWEETRPG_ROOT_URL) or "/"

    # Build info for footer - set by CI/CD during image build
    BUILD_TIMESTAMP = os.environ.get("BUILD_TIMESTAMP") or "unknown"
    BUILD_HASH = os.environ.get("BUILD_HASH") or "unknown"
