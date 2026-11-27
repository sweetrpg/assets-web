# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""test_permissions.py
Tests for who may write and delete each asset kind.
"""

import io
import logging
from pathlib import Path

import pytest
import requests

from conftest import authenticate

OWNER_SUB = "auth0|abc123"
OWNER_ID = "auth0-abc123"
PUBLISHED_KINDS = ("avatar", "map", "token", "portrait", "cover", "sample")


def _post(client, kind, id):
    return client.post(
        f"/asset/{kind}/{id}",
        data={"file": (io.BytesIO(b"new-bytes"), "a.png", "image/png")},
        content_type="multipart/form-data",
    )


def _seed(app, kind, id):
    directory = Path(app.config["ASSET_DATA_PATH"]) / kind / id
    directory.mkdir(parents=True)
    (directory / "image.png").write_bytes(b"original")
    return directory / "image.png"


def _login(client, auth_api, roles, sub=OWNER_SUB):
    authenticate(client, sub=sub)
    auth_api.body = {"allowed": True, "roles": roles}


@pytest.mark.parametrize("roles", [["user"], ["submitter"], ["openfga-writer"], []])
@pytest.mark.parametrize("kind", PUBLISHED_KINDS)
def test_published_write_and_delete_need_editor_or_admin(app, client, auth_api, kind, roles):
    stored = _seed(app, kind, "vol1")
    _login(client, auth_api, roles)

    assert _post(client, kind, "vol1").status_code == 403
    assert client.delete(f"/asset/{kind}/vol1").status_code == 403
    assert stored.read_bytes() == b"original"


@pytest.mark.parametrize("role", ["editor", "admin"])
@pytest.mark.parametrize("kind", PUBLISHED_KINDS)
def test_editor_and_admin_write_and_delete_published(client, auth_api, kind, role):
    _login(client, auth_api, [role])

    assert _post(client, kind, "vol1").status_code == 201
    assert client.delete(f"/asset/{kind}/vol1").status_code == 204


def test_session_roles_are_not_trusted(client, auth_api):
    # The shared session says "editor"; auth-api is the authority.
    _login(client, auth_api, ["user"])

    assert _post(client, "cover", "vol1").status_code == 403


@pytest.mark.parametrize(
    "kind,id",
    [
        ("cover-staged", OWNER_ID),
        ("cover-staged", f"{OWNER_ID}-1732000000000"),
        ("sample-staged", f"{OWNER_ID}-0"),
        ("sample-staged", f"{OWNER_ID}-12"),
    ],
)
@pytest.mark.parametrize("role", ["submitter", "editor", "admin"])
def test_owner_writes_and_deletes_own_staged(client, auth_api, kind, id, role):
    _login(client, auth_api, [role])

    assert _post(client, kind, id).status_code == 201
    assert client.delete(f"/asset/{kind}/{id}").status_code == 204


@pytest.mark.parametrize(
    "kind,id",
    [
        ("cover-staged", "auth0-other"),
        ("cover-staged", f"{OWNER_ID}-x"),
        ("cover-staged", f"{OWNER_ID}-1-0"),
        ("cover-staged", "auth0-abc12"),
        ("sample-staged", "auth0-other-0"),
        ("sample-staged", OWNER_ID),
        ("sample-staged", f"{OWNER_ID}-x"),
        ("sample-staged", f"{OWNER_ID}-1-0"),
    ],
)
def test_non_owner_cannot_write_or_delete_staged(app, client, auth_api, kind, id):
    stored = _seed(app, kind, id)
    _login(client, auth_api, ["submitter"])

    assert _post(client, kind, id).status_code == 403
    assert client.delete(f"/asset/{kind}/{id}").status_code == 403
    assert stored.read_bytes() == b"original"


@pytest.mark.parametrize("roles", [["user"], ["openfga-writer"], []])
def test_owner_without_write_role_can_remove_but_not_write_staged(app, client, auth_api, roles):
    stored = _seed(app, "cover-staged", OWNER_ID)
    _login(client, auth_api, roles)

    assert _post(client, "cover-staged", OWNER_ID).status_code == 403
    assert stored.read_bytes() == b"original"
    assert client.delete(f"/asset/cover-staged/{OWNER_ID}").status_code == 204


@pytest.mark.parametrize("role", ["editor", "admin"])
def test_reviewer_cannot_overwrite_but_can_remove_anothers_staged(app, client, auth_api, role):
    # catalog-api's accept promotes with the reviewer's bearer: read, store live, delete staged.
    _seed(app, "cover-staged", "auth0-other")
    _login(client, auth_api, [role])

    assert _post(client, "cover-staged", "auth0-other").status_code == 403
    assert client.get("/asset/cover-staged/auth0-other").status_code == 200
    assert _post(client, "cover", "vol1").status_code == 201
    assert client.delete("/asset/cover-staged/auth0-other").status_code == 204


def test_auth_api_receives_the_callers_own_token(client, auth_api):
    _login(client, auth_api, ["editor"])

    _post(client, "cover", "vol1")

    url, kwargs = auth_api.calls[0]
    assert url == "http://auth-api.test/authz/check"
    assert kwargs["headers"] == {"Authorization": "Bearer session-access-token"}
    assert kwargs["json"]["service"] == "assets-web"
    assert kwargs["allow_redirects"] is False
    assert kwargs["timeout"]


@pytest.mark.parametrize(
    "status,body,error,expected",
    [
        (200, {"allowed": False, "reason": "service_denied"}, None, 403),
        (200, {"allowed": False, "roles": ["admin"]}, None, 403),
        (401, {"error": "invalid_token"}, None, 401),
        (500, {"allowed": True, "roles": ["admin"]}, None, 503),
        (302, {}, None, 503),
        (200, ValueError("not json"), None, 503),
        (200, ["admin"], None, 503),
        (200, {"allowed": True, "roles": "admin"}, None, 503),
        (200, {}, requests.exceptions.ConnectTimeout("down"), 503),
    ],
)
def test_fails_closed_when_roles_cannot_be_read(app, client, auth_api, status, body, error, expected):
    stored = _seed(app, "cover", "vol1")
    authenticate(client)
    auth_api.status, auth_api.body, auth_api.error = status, body, error

    assert _post(client, "cover", "vol1").status_code == expected
    assert client.delete("/asset/cover/vol1").status_code == expected
    assert stored.read_bytes() == b"original"


@pytest.mark.parametrize("kind,id", [("cover", "vol1"), ("cover-staged", "github-1")])
def test_fails_closed_without_auth_api_url(app, client, kind, id):
    app.config["AUTH_API_URL"] = None
    authenticate(client)

    assert _post(client, kind, id).status_code == 503


@pytest.mark.parametrize("id", ["..", ".", "..%5C..", "a%20b", ".hidden", "%2E%2E"])
def test_unsafe_ids_rejected_on_write_and_delete(app, client, auth_api, id):
    stored = _seed(app, "cover", "vol1")
    _login(client, auth_api, ["admin"])

    assert _post(client, "cover", id).status_code in (400, 404, 405)
    assert client.delete(f"/asset/cover/{id}").status_code in (400, 404, 405)
    assert stored.read_bytes() == b"original"


@pytest.mark.parametrize("kind", ["..", "%2E%2E", "cover%2F.."])
def test_unsafe_kinds_rejected(client, auth_api, kind):
    _login(client, auth_api, ["admin"])

    assert client.delete(f"/asset/{kind}/vol1").status_code in (400, 404, 405)


def test_credentials_are_not_logged_or_persisted(app, client, auth_api, caplog):
    _login(client, auth_api, ["editor"])
    client.set_cookie("sweetrpg-auth", "cookie-secret")
    caplog.set_level(logging.DEBUG)
    app.logger.setLevel(logging.DEBUG)
    app.logger.addHandler(caplog.handler)

    client.post("/asset/cover/vol1", headers={"Authorization": "Bearer header-secret"})
    _post(client, "cover", "vol1")

    for secret in ("session-access-token", "header-secret", "cookie-secret", "test-session-id", "test@example.com"):
        assert secret not in caplog.text
    with client.session_transaction() as flask_session:
        assert "session-access-token" not in str(dict(flask_session))
        assert "cookie-secret" not in str(dict(flask_session))


def test_unexpected_errors_do_not_expose_details(client, auth_api, monkeypatch):
    from sweetrpg_assets_web.application.cache import cache

    def _boom(key):
        raise RuntimeError("redis://:internal-detail@cache:6379")

    monkeypatch.setattr(cache, "get", _boom)

    response = client.get("/asset/cover/vol1")

    assert response.status_code == 500
    assert response.get_json() == {"message": "Internal server error"}


def test_reclaim_failure_does_not_expose_details(app, client):
    app.config["RECLAIM_JOB_TOKEN"] = "job-token"
    app.config["CATALOG_API_URL"] = None

    response = client.post("/admin/reclaim-staged-assets", headers={"X-Reclaim-Token": "job-token"})

    assert response.status_code == 503
    assert "CATALOG_API_URL" not in response.get_data(as_text=True)


def test_session_without_access_token_cannot_write(app, client, auth_api):
    from sweetrpg_assets_web.application import permissions

    with app.test_request_context():
        with pytest.raises(Exception) as raised:
            permissions.require_asset_permission({"sub": OWNER_SUB}, "cover", "vol1", deleting=False)

    assert raised.value.code == 401
    assert auth_api.calls == []


def test_bearer_caller_is_checked_with_the_forwarded_token(app, client, auth_api, monkeypatch):
    from test_bearer_token import _configure, _make_key, _token

    _configure(app, monkeypatch)
    token = _token(app, _make_key(monkeypatch))
    auth_api.body = {"allowed": True, "roles": ["user"]}

    response = client.post(
        "/asset/cover/vol1",
        data={"file": (io.BytesIO(b"x"), "a.png", "image/png")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert auth_api.calls[0][1]["headers"] == {"Authorization": f"Bearer {token}"}


def test_asset_dir_that_resolves_outside_the_data_path_is_rejected(app, client, auth_api, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")
    (outside / "image.png").write_bytes(b"original")
    (Path(app.config["ASSET_DATA_PATH"]) / "cover").mkdir()
    (Path(app.config["ASSET_DATA_PATH"]) / "cover" / "linked").symlink_to(outside)
    _login(client, auth_api, ["admin"])

    assert _post(client, "cover", "linked").status_code == 400
    assert client.delete("/asset/cover/linked").status_code == 400
    assert (outside / "image.png").read_bytes() == b"original"
