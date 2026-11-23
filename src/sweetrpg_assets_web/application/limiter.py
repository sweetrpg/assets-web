# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""limiter.py

Process-wide rate limit: one shared bucket across every route and every client, not per-client
throttling - matches the Go services' `golang.org/x/time/rate` middleware convention (a blunt
backstop, not real per-client rate limiting). The key function returns a constant so every
request shares the same bucket regardless of caller; the limit string comes from `RATE_LIMIT`
via `BaseConfig`, applied globally in `create_app`.

The limiter uses a fail-open Redis storage wrapper so that when Redis is unavailable (e.g.
during cache pod restarts), requests are allowed through rather than returning 500. This
prevents the rate limiter from becoming a single point of failure that takes down the entire
service. The actual per-client rate limiting is handled at the infrastructure layer (Traefik,
cloud firewall).
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from limits.storage import RedisStorage
from limits.storage.base import Storage
import redis
import logging

logger = logging.getLogger(__name__)


class FailOpenRedisStorage(RedisStorage):
    """Redis storage wrapper that fails open (allows requests) when Redis is unavailable.

    When Redis connection fails, instead of raising an exception that results in HTTP 500,
    this storage returns a "limit not exceeded" response, allowing the request to proceed.
    This is appropriate because:
    1. The Flask-Limiter is a blunt backstop (global shared bucket), not real per-client limiting
    2. Real per-client rate limiting is handled at the infrastructure layer (Traefik, cloud firewall)
    3. It's better to allow traffic during Redis outages than to take the service down
    """

    # Override the default RedisStorage for redis:// and rediss:// schemes
    STORAGE_SCHEME = [
        "redis",
        "rediss",
        "redis+unix",
        "valkey",
        "valkeys",
        "valkey+unix",
    ]

    def __init__(self, uri: str, **options):
        super().__init__(uri, **options)
        self._fail_open = True

    def _handle_error(self, operation: str, error: Exception):
        """Log the error and return a fail-open result."""
        logger.warning(
            "Rate limiter Redis error during %s, failing open: %s",
            operation,
            error,
        )
        # Return a result indicating the limit was not exceeded (fail-open)
        return True

    def incr(self, key: str, expiry: int, amount: int = 1):
        try:
            return super().incr(key, expiry, amount)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._handle_error("incr", e)
            return 0  # Fail open: pretend we didn't hit the limit

    def get(self, key: str):
        try:
            return super().get(key)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._handle_error("get", e)
            return 0  # Fail open

    def get_expiry(self, key: str):
        try:
            return super().get_expiry(key)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._handle_error("get_expiry", e)
            return 0

    def check(self):
        """Health check for the storage backend."""
        try:
            return super().check()
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._handle_error("check", e)
            return False

    def reset(self):
        try:
            return super().reset()
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._handle_error("reset", e)
            return True

    def clear(self, key: str):
        try:
            return super().clear(key)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._handle_error("clear", e)
            return True


# Limiter instance - storage will be configured in create_app() after config is loaded
# We create it without storage initially, then replace it in create_app()
limiter = None


def create_limiter(storage_uri: str) -> Limiter:
    """Create a Limiter instance with fail-open Redis storage."""
    return Limiter(
        key_func=lambda: "global",
        storage_uri=storage_uri,
    )