# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""test_quota.py
Tests for the per-user bound on staged uploads.
"""

import io
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import redis as redis_lib

from conftest import authenticate

SUB = "auth0|abc123"
OWNER = "auth0-abc123"


@pytest.fixture(autouse=True)
def _limits(app, auth_api):
    app.config["STAGED_MAX_FILES"] = 3
    app.config["STAGED_MAX_BYTES"] = 100
    auth_api.body = {"allowed": True, "roles": ["submitter"]}


@pytest.fixture
def user(client):
    authenticate(client, sub=SUB)
    return client


def _post(client, kind, id, size=10):
    return client.post(
        f"/asset/{kind}/{id}",
        data={"file": (io.BytesIO(b"x" * size), "a.png", "image/png")},
        content_type="multipart/form-data",
    )


def _staged_dirs(app):
    base = Path(app.config["ASSET_DATA_PATH"])
    return sorted(f"{p.parent.name}/{p.name}" for p in base.glob("*-staged/*"))


def test_file_limit_counts_covers_and_samples_together(app, user):
    assert _post(user, "cover-staged", OWNER).status_code == 201
    assert _post(user, "cover-staged", f"{OWNER}-1").status_code == 201
    assert _post(user, "sample-staged", f"{OWNER}-2").status_code == 201

    response = _post(user, "sample-staged", f"{OWNER}-3")

    assert response.status_code == 409
    assert "limit" in response.get_json()["message"].lower()
    assert len(_staged_dirs(app)) == 3


def test_byte_limit_allows_exactly_the_limit_and_no_more(app, user):
    assert _post(user, "sample-staged", f"{OWNER}-0", size=60).status_code == 201
    assert _post(user, "sample-staged", f"{OWNER}-1", size=40).status_code == 201

    assert _post(user, "sample-staged", f"{OWNER}-2", size=1).status_code == 409
    assert _staged_dirs(app) == [f"sample-staged/{OWNER}-0", f"sample-staged/{OWNER}-1"]


def test_replacement_is_not_counted_twice(user):
    for index in range(3):
        assert _post(user, "sample-staged", f"{OWNER}-{index}", size=30).status_code == 201

    assert _post(user, "sample-staged", f"{OWNER}-0", size=40).status_code == 201


def test_rejected_replacement_keeps_the_original(app, user):
    _post(user, "cover-staged", OWNER, size=50)
    _post(user, "sample-staged", f"{OWNER}-0", size=50)

    assert _post(user, "cover-staged", OWNER, size=51).status_code == 409
    stored = Path(app.config["ASSET_DATA_PATH"]) / "cover-staged" / OWNER / "image.png"
    assert stored.stat().st_size == 50


def test_delete_frees_room(user):
    for index in range(3):
        _post(user, "sample-staged", f"{OWNER}-{index}")
    assert user.delete(f"/asset/sample-staged/{OWNER}-0").status_code == 204

    assert _post(user, "sample-staged", f"{OWNER}-9").status_code == 201


@pytest.mark.parametrize("other", ["auth0-abc1234", "auth0-abc12", "github-1"])
def test_other_users_files_do_not_count(app, user, other):
    for kind, name in (("cover-staged", other), ("sample-staged", f"{other}-0")):
        directory = Path(app.config["ASSET_DATA_PATH"]) / kind / name
        directory.mkdir(parents=True)
        (directory / "image.png").write_bytes(b"x" * 500)

    assert _post(user, "cover-staged", OWNER).status_code == 201


def test_published_uploads_are_not_limited(user, auth_api):
    auth_api.body = {"allowed": True, "roles": ["editor"]}

    for index in range(5):
        assert _post(user, "cover", f"vol{index}", size=200).status_code == 201


def test_parallel_uploads_cannot_exceed_the_limit(app, monkeypatch):
    from sweetrpg_assets_web.application import quota

    real_usage = quota._usage

    def _slow_usage(*args):
        result = real_usage(*args)
        time.sleep(0.05)  # widens the gap between the check and the write
        return result

    monkeypatch.setattr(quota, "_usage", _slow_usage)

    def _upload(index):
        client = app.test_client()
        authenticate(client, sub=SUB)
        return _post(client, "sample-staged", f"{OWNER}-{index}").status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(_upload, range(8)))

    assert sorted(statuses) == [201] * 3 + [409] * 5
    assert len(_staged_dirs(app)) == 3


def test_lock_held_elsewhere_refuses_the_upload(app, user, monkeypatch):
    from sweetrpg_assets_web.application import quota

    monkeypatch.setattr(quota, "LOCK_WAIT_SECONDS", 0.1)
    lock = app.config["SESSION_REDIS"].lock(f"staged-upload-lock:{OWNER}", timeout=5)
    assert lock.acquire()
    try:
        assert _post(user, "cover-staged", OWNER).status_code == 503
    finally:
        lock.release()
    assert _staged_dirs(app) == []


def test_unreachable_lock_store_refuses_the_upload(app, user):
    app.config["SESSION_REDIS"] = redis_lib.Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.1)

    assert _post(user, "cover-staged", OWNER).status_code == 503
    assert _staged_dirs(app) == []


def test_lock_lost_before_release_does_not_fail_a_finished_upload(app, user, monkeypatch):
    from sweetrpg_assets_web.application import quota

    real_usage = quota._usage

    def _expire_lock(*args):
        app.config["SESSION_REDIS"].delete(f"staged-upload-lock:{OWNER}")
        return real_usage(*args)

    monkeypatch.setattr(quota, "_usage", _expire_lock)

    assert _post(user, "cover-staged", OWNER).status_code == 201


def test_unreadable_usage_refuses_the_upload(app, user, monkeypatch):
    from sweetrpg_assets_web.application import quota

    def _boom(*args):
        raise PermissionError("no")

    monkeypatch.setattr(quota, "_usage", _boom)

    assert _post(user, "cover-staged", OWNER).status_code == 503
    assert _staged_dirs(app) == []


@pytest.mark.parametrize("value", ["0", "-1", "many"])
def test_invalid_limit_setting_is_rejected(monkeypatch, value):
    from sweetrpg_assets_web.application.config import _env_positive_int

    monkeypatch.setenv("STAGED_MAX_FILES", value)

    with pytest.raises(ValueError):
        _env_positive_int("STAGED_MAX_FILES", 200)
