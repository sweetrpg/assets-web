# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""constants.py
Constants for keys and environment variable names
"""

AUTH0_CLIENT_ID = "AUTH0_CLIENT_ID"
AUTH0_CLIENT_SECRET = "AUTH0_CLIENT_SECRET"
AUTH0_CALLBACK_URL = "AUTH0_CALLBACK_URL"
AUTH0_DOMAIN = "AUTH0_DOMAIN"
AUTH0_AUDIENCE = "AUTH0_AUDIENCE"
AUTH0_LOGIN_URL = "AUTH0_LOGIN_URL"

KANKA_CLIENT_ID = "KANKA_CLIENT_ID"
KANKA_CLIENT_SECRET = "KANKA_CLIENT_SECRET"
KANKA_CALLBACK_URL = "KANKA_CALLBACK_URL"
KANKA_DOMAIN = "KANKA_DOMAIN"
KANKA_AUDIENCE = "KANKA_AUDIENCE"

SENTRY_DSN = "SENTRY_DSN"
SENTRY_ENV = "SENTRY_ENV"

APPLICATION_NAME = "sweetrpg-assets-web"

# session keys
PROFILE_KEY = "profile"
JWT_PAYLOAD = "jwt_payload"
CURRENT_USER_ID = "current_user_id"
SESSION_ACCESS_TOKEN = "access_token"
SESSION_EMAIL = "email"
SESSION_USER_ID = "user_id"

# global keys
SWEETRPG_API_CLIENT_KEY = "sweetrpg-api-client"

# cookies
SWEETRPG_AUTH_KEY = "sweetrpg-auth"

# Configuration
SEGMENT_WRITE_KEY = "SEGMENT_WRITE_KEY"
DEBUG = "DEBUG"
PORT = "PORT"
LOG_LEVEL = "LOG_LEVEL"
DB_HOST = "DB_HOST"
DB_PORT = "DB_PORT"
DB_USER = "DB_USER"
DB_PW = "DB_PW"
DB_NAME = "DB_NAME"
DB_OPTS = "DB_OPTS"
REDIS_HOST = "REDIS_HOST"
REDIS_PORT = "REDIS_PORT"
REDIS_DB = "REDIS_DB"
REDIS_PASS = "REDIS_PASS"
LOGSTASH_HOST = "LOGSTASH_HOST"
LOGSTASH_DB_PATH = "LOGSTASH_DB_PATH"
LOGSTASH_TRANSPORT = "LOGSTASH_TRANSPORT"
LOGSTASH_PORT = "LOGSTASH_PORT"

SHELF_API_BASE_URL = "SHELF_API_BASE_URL"
# Prefix this app is mounted under behind the reverse proxy (e.g. "/assets") - Traefik strips it
# before the request reaches this pod, so it must be re-added to every url_for()-generated link.
# See PrefixMiddleware in main.py. Previously unused (always ""); now consumed there.
APPLICATION_BASE_PATH = "APPLICATION_BASE_PATH"

# Suite-wide platform root (see docs/frontend-conventions.md in sweetrpg/platform)
SWEETRPG_ROOT_URL = "SWEETRPG_ROOT_URL"

# admin-api integration (banners, maintenance mode)
ADMIN_API_URL = "ADMIN_API_URL"
MAINTENANCE_MODE_SCOPES = ["platform", "service:assets"]

# Path to the build-info.json the Docker build writes (see Dockerfile) - already present as a
# configmap key, previously unused by any code.
BUILD_INFO_PATH = "BUILD_INFO_PATH"

# Asset storage
ASSET_DATA_PATH = "ASSET_DATA_PATH"
ASSET_CACHE_TTL = "ASSET_CACHE_TTL"
ALLOWED_KINDS = frozenset(
    {
        "avatar",
        "map",
        "token",
        "portrait",
        "cover",
        "cover-staged",
        "sample",
        "sample-staged",
    }
)
MAX_ASSET_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_CONTENT_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})

# Rate limiting
RATE_LIMIT = "RATE_LIMIT"

# Tracing
OTEL_EXPORTER_OTLP_ENDPOINT = "OTEL_EXPORTER_OTLP_ENDPOINT"
