# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""test_reclaim.py
Tests for the staged-asset reclaim job (durable-volume-editing task 2.4).
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
import redis as redis_lib

RECLAIM_TOKEN = "test-reclaim-token"
EDIT_SESSION_DB = 9


def _make_catalog_api(cover_ids, sample_ids):
    return _serve(json.dumps({"coverAssetIds": cover_ids, "sampleAssetIds": sample_ids}).encode())


def _serve(body: bytes, status: int = 200, headers: dict | None = None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
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


def _stage(app, kind, id, data=b"staged-bytes"):
    directory = Path(app.config["ASSET_DATA_PATH"]) / kind / id
    directory.mkdir(parents=True)
    (directory / "image.png").write_bytes(data)


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
    _stage(reclaim_app, "cover-staged", "orphan-1")

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
    _stage(reclaim_app, "cover-staged", "live-1")
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
    _stage(reclaim_app, "cover-staged", "github-419457")
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
    _stage(reclaim_app, "sample-staged", "pending-1-0")

    resp = reclaim_app.test_client().post(
        "/admin/reclaim-staged-assets", headers={"X-Reclaim-Token": RECLAIM_TOKEN}
    )
    assert resp.status_code == 200
    assert resp.json["deleted"] == []
    assert _asset_dir_exists(reclaim_app, "sample-staged", "pending-1-0")
    catalog_api.shutdown()


@pytest.mark.parametrize("cover_id", ["auth0-abc123", "auth0-abc123-1732000000000"])
def test_reclaim_keeps_cover_referenced_by_live_session(reclaim_app, edit_session_redis, cover_id):
    catalog_api = _make_catalog_api([], [])
    reclaim_app.config["CATALOG_API_URL"] = f"http://127.0.0.1:{catalog_api.server_port}"
    _stage(reclaim_app, "cover-staged", cover_id)
    edit_session_redis.set("edit-session:auth0|abc123:volume", json.dumps({"stagedCoverAssetId": cover_id}))

    resp = reclaim_app.test_client().post(
        "/admin/reclaim-staged-assets", headers={"X-Reclaim-Token": RECLAIM_TOKEN}
    )

    assert resp.json["deleted"] == []
    assert _asset_dir_exists(reclaim_app, "cover-staged", cover_id)
    catalog_api.shutdown()


_VALID = b'{"coverAssetIds": [], "sampleAssetIds": []}'


@pytest.mark.parametrize(
    "body,status",
    [
        pytest.param(b"{}", 200, id="both-keys-missing"),
        pytest.param(b'{"sampleAssetIds": []}', 200, id="covers-missing"),
        pytest.param(b'{"coverAssetIds": []}', 200, id="samples-missing"),
        pytest.param(b'{"coverAssetIds": null, "sampleAssetIds": []}', 200, id="covers-null"),
        pytest.param(b'{"coverAssetIds": [], "sampleAssetIds": null}', 200, id="samples-null"),
        pytest.param(b'{"coverAssetIds": "", "sampleAssetIds": []}', 200, id="covers-string"),
        pytest.param(b'{"coverAssetIds": [], "sampleAssetIds": {}}', 200, id="samples-object"),
        pytest.param(b'{"coverAssetIds": 0, "sampleAssetIds": []}', 200, id="covers-number"),
        pytest.param(b'{"coverAssetIds": [], "sampleAssetIds": false}', 200, id="samples-bool"),
        pytest.param(b'{"coverAssetIds": [1], "sampleAssetIds": []}', 200, id="element-number"),
        pytest.param(b'{"coverAssetIds": [], "sampleAssetIds": [null]}', 200, id="element-null"),
        pytest.param(b"[]", 200, id="top-level-array"),
        pytest.param(b"null", 200, id="top-level-null"),
        pytest.param(b'"ok"', 200, id="top-level-string"),
        pytest.param(b"not json", 200, id="parse-failure"),
        pytest.param(b"", 200, id="empty-body"),
        pytest.param(_VALID, 201, id="status-201"),
        pytest.param(_VALID, 203, id="status-203"),
        pytest.param(_VALID, 404, id="status-404"),
        pytest.param(_VALID, 500, id="status-500"),
    ],
)
def test_reclaim_deletes_nothing_on_bad_pending_response(reclaim_app, caplog, body, status):
    _assert_aborts_without_deleting(reclaim_app, caplog, _serve(body, status))


def test_reclaim_does_not_follow_pending_redirect(reclaim_app, caplog):
    target = _serve(_VALID)
    location = f"http://127.0.0.1:{target.server_port}/elsewhere"
    _assert_aborts_without_deleting(reclaim_app, caplog, _serve(_VALID, 302, {"Location": location}))
    target.shutdown()


def _assert_aborts_without_deleting(app, caplog, catalog_api):
    app.config["CATALOG_API_URL"] = f"http://127.0.0.1:{catalog_api.server_port}"
    _stage(app, "cover-staged", "orphan-1")
    _stage(app, "sample-staged", "orphan-1-0")
    # create_app's dictConfig disables loggers left over from earlier tests' apps.
    app.logger.disabled = False
    caplog.clear()

    resp = app.test_client().post("/admin/reclaim-staged-assets", headers={"X-Reclaim-Token": RECLAIM_TOKEN})
    catalog_api.shutdown()

    assert resp.status_code == 503
    assert _asset_dir_exists(app, "cover-staged", "orphan-1")
    assert _asset_dir_exists(app, "sample-staged", "orphan-1-0")
    assert any(r.levelname == "ERROR" for r in caplog.records)
    assert RECLAIM_TOKEN not in caplog.text
    assert "orphan-1" not in caplog.text
