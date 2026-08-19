# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""conftest.py
Shared fixtures for the test suite.
"""

import datetime
import json
import os

import pytest
import redis as redis_lib

SHARED_SESSION_DB = 10


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("ASSET_DATA_PATH", str(tmp_path))
    # Distinct db from CACHE_REDIS_DB's default (7) and test_reclaim.py's EDIT_SESSION_DB (9) -
    # see shared_session.py.
    monkeypatch.setenv("SHARED_SESSION_REDIS_HOST", "localhost")
    monkeypatch.setenv("SHARED_SESSION_REDIS_DB", "10")

    from sweetrpg_assets_web.application.main import create_app

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    # BaseConfig's class attributes are computed once, at that module's first import - a later
    # test's monkeypatch.setenv("ASSET_DATA_PATH", ...) has no effect on them. Overriding the
    # (mutable) Flask config dict directly guarantees each test gets its own tmp_path, instead
    # of every test in the process sharing whichever tmp_path happened to trigger that import.
    flask_app.config["ASSET_DATA_PATH"] = str(tmp_path)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _clean_shared_session_db():
    conn = redis_lib.Redis(host="localhost", port=6379, db=SHARED_SESSION_DB)
    conn.flushdb()
    yield
    conn.flushdb()


def authenticate(client, sub="github|1", email="test@example.com", session_id="test-session-id"):
    """Writes a valid shared-session entry (auth-web's schema - see shared_session.py) and sets
    the sweetrpg_session cookie so this client reads as logged in as `sub`."""
    user = json.dumps(
        {
            "sub": sub,
            "name": "Test User",
            "email": email,
            "roles": ["editor"],
            "expiry": (
                datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
            ).isoformat(),
        }
    )
    conn = redis_lib.Redis(host="localhost", port=6379, db=SHARED_SESSION_DB, decode_responses=True)
    conn.set(f"vrs-{session_id}", json.dumps({"user": user}))
    client.set_cookie("sweetrpg_session", session_id)
