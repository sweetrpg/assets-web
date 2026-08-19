# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""shared_session.py

Read-only access to the suite-wide login session `auth-web` writes under the `sweetrpg_session`
cookie (see docs/frontend-conventions.md's "Shared session schema" in sweetrpg/platform, and
catalog-web's SessionUserAccess.swift for the reference implementation every other frontend
follows). This app previously expected an upstream Traefik ForwardAuth middleware to verify the
session and inject X-Forwarded-User/X-Forwarded-Email headers - that middleware was never built
anywhere in the platform, so every authenticated write (POST/DELETE /asset/<kind>/<id>) 401'd
unconditionally. Reading the shared session directly matches every other *-web frontend and
needs no new infrastructure.

Fails open (returns None) on every error path: unconfigured, unreachable Redis, missing cookie,
missing key, malformed JSON, expired session - same fail-open contract as every other frontend's
read-only shared-session client. Never writes to this Redis connection.
"""

import datetime
import json

import redis
from flask import current_app, request

SESSION_COOKIE_NAME = "sweetrpg_session"


def _client() -> redis.Redis | None:
    host = current_app.config.get("SHARED_SESSION_REDIS_HOST")
    if not host:
        return None
    return redis.Redis(
        host=host,
        port=current_app.config["SHARED_SESSION_REDIS_PORT"],
        db=current_app.config["SHARED_SESSION_REDIS_DB"],
        password=current_app.config.get("SHARED_SESSION_REDIS_PASSWORD") or None,
        decode_responses=True,
    )


def current_user() -> dict | None:
    """Returns the shared session's user dict (sub, name, email, roles, expiry) if the visitor
    has a valid, unexpired session; None otherwise."""
    client = _client()
    if client is None:
        return None

    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return None

    try:
        # Key format matches ResilientRedisSessionDriver (auth-web's session writer):
        # `vrs-<sessionID>`, JSON-encoded Vapor SessionData (a flat {"user": "<json-string>"}).
        raw = client.get(f"vrs-{session_id}")
        if raw is None:
            return None
        session_data = json.loads(raw)
        user = json.loads(session_data["user"])
        expiry = datetime.datetime.fromisoformat(user["expiry"])
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=datetime.timezone.utc)
        if expiry <= datetime.datetime.now(datetime.timezone.utc):
            return None
        return user
    except Exception:
        current_app.logger.warning("shared_session.current_user failed", exc_info=True)
        return None
