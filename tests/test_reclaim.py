# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""test_reclaim.py
Tests for the staged-asset reclaim job (durable-volume-editing task 2.4).
"""

import io
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
import redis as redis_lib

from conftest import authenticate

RECLAIM_TOKEN = "test-reclaim-token"
EDIT_SESSION_DB = 9


def _make_catalog_api(cover_ids, sample_ids):
    body = json.dumps({"coverAssetIds": cover_ids, "sampleAssetIds": sample_ids}).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


@pytest.fixture
def edit_session_redis():
    client = redis_lib.Redis(host="localhost", port=6379, db=EDIT_SESSION_DB, decode_responses=True)
    client.flushdb()
    yield client
    client.flushdb()


@pytest.fixture
def reclaim_app(app, edit_session_redis):
    app.config["RECLAIM_JOB_TOKEN"] = RECLAIM_TOKEN
    app.config["EDIT_SESSION_REDIS_HOST"] = "localhost"
    app.config["EDIT_SESSION_REDIS_PORT"] = 6379
    app.config["EDIT_SESSION_REDIS_DB"] = EDIT_SESSION_DB
    return app


def _stage(app, kind, id, owner_id, data=b"staged-bytes"):
    client = app.test_client()
    authenticate(client, sub=f"auth0|{owner_id}", email="t@example.com", session_id=f"session-{owner_id}-{kind}-{id}")
    client.post(
        f"/asset/{kind}/{id}",
        data={"file": (io.BytesIO(data), "a.png")},
        content_type="multipart/form-data",
    )


def _asset_dir_exists(app, kind, id) -> bool:
    return (Path(app.config["ASSET_DATA_PATH"]) / kind / id).is_dir()


def test_reclaim_requires_token(reclaim_app):
    resp = reclaim_app.test_client().post("/admin/reclaim-staged-assets")
    assert resp.status_code == 401


def test_reclaim_503s_when_dependencies_unconfigured(app):
    app.config["RECLAIM_JOB_TOKEN"] = RECLAIM_TOKEN
    resp = app.test_client().post(
        "/admin/reclaim-staged-assets", headers={"X-Reclaim-Token": RECLAIM_TOKEN}
    )
    assert resp.status_code == 503


def test_reclaim_deletes_orphaned_cover(reclaim_app):
    catalog_api = _make_catalog_api([], [])
    reclaim_app.config["CATALOG_API_URL"] = f"http://127.0.0.1:{catalog_api.server_port}"
    _stage(reclaim_app, "cover-staged", "orphan-1", owner_id="orphan-1")

    resp = reclaim_app.test_client().post(
        "/admin/reclaim-staged-assets", headers={"X-Reclaim-Token": RECLAIM_TOKEN}
    )
    assert resp.status_code == 200
    assert resp.json["deleted"] == ["cover-staged/orphan-1"]
    assert not _asset_dir_exists(reclaim_app, "cover-staged", "orphan-1")
    catalog_api.shutdown()


def test_reclaim_keeps_cover_referenced_by_live_session(reclaim_app, edit_session_redis):
    catalog_api = _make_catalog_api([], [])
    reclaim_app.config["CATALOG_API_URL"] = f"http://127.0.0.1:{catalog_api.server_port}"
    _stage(reclaim_app, "cover-staged", "live-1", owner_id="live-1")
    edit_session_redis.set(
        "edit-session:live-1:volume",
        json.dumps({"recordId": "vol-1", "fields": {}, "stagedCoverAssetId": "live-1"}),
    )

    resp = reclaim_app.test_client().post(
        "/admin/reclaim-staged-assets", headers={"X-Reclaim-Token": RECLAIM_TOKEN}
    )
    assert resp.status_code == 200
    assert resp.json["deleted"] == []
    assert _asset_dir_exists(reclaim_app, "cover-staged", "live-1")
    catalog_api.shutdown()


def test_reclaim_keeps_cover_referenced_by_live_session_with_piped_sub(reclaim_app, edit_session_redis):
    # Regression test: catalog-web's sanitizedAssetUserID turns a raw Auth0 sub like
    # "github|419457" into "github-419457" for the staged asset id, but the edit-session Redis
    # key is written under the RAW, unsanitized sub. The reclaim job must match a staged asset
    # id back to its live session despite this - see reclaim.py's _sanitized_user_id.
    catalog_api = _make_catalog_api([], [])
    reclaim_app.config["CATALOG_API_URL"] = f"http://127.0.0.1:{catalog_api.server_port}"
    _stage(reclaim_app, "cover-staged", "github-419457", owner_id="github-419457")
    edit_session_redis.set(
        "edit-session:github|419457:volume",
        json.dumps({"recordId": "vol-1", "fields": {}, "stagedCoverAssetId": "github-419457"}),
    )

    resp = reclaim_app.test_client().post(
        "/admin/reclaim-staged-assets", headers={"X-Reclaim-Token": RECLAIM_TOKEN}
    )
    assert resp.status_code == 200
    assert resp.json["deleted"] == []
    assert _asset_dir_exists(reclaim_app, "cover-staged", "github-419457")
    catalog_api.shutdown()


def test_reclaim_keeps_sample_referenced_by_pending_submission(reclaim_app):
    catalog_api = _make_catalog_api([], ["pending-1-0"])
    reclaim_app.config["CATALOG_API_URL"] = f"http://127.0.0.1:{catalog_api.server_port}"
    _stage(reclaim_app, "sample-staged", "pending-1-0", owner_id="pending-1")

    resp = reclaim_app.test_client().post(
        "/admin/reclaim-staged-assets", headers={"X-Reclaim-Token": RECLAIM_TOKEN}
    )
    assert resp.status_code == 200
    assert resp.json["deleted"] == []
    assert _asset_dir_exists(reclaim_app, "sample-staged", "pending-1-0")
    catalog_api.shutdown()
