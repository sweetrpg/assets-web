# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""conftest.py
Shared fixtures for the test suite.
"""

import os

import pytest


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("ASSET_DATA_PATH", str(tmp_path))

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
