# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""test_assets.py
Tests for the asset storage routes.
"""

import io

AUTH_HEADERS = {
    "X-Forwarded-User": "github|1",
    "X-Forwarded-Email": "test@example.com",
}


def _upload(client, kind, id, filename="a.png", data=b"pixels", headers=AUTH_HEADERS):
    return client.post(
        f"/asset/{kind}/{id}",
        data={"file": (io.BytesIO(data), filename)},
        content_type="multipart/form-data",
        headers=headers,
    )


def test_store_requires_authentication(client):
    resp = _upload(client, "avatar", "1", headers={})
    assert resp.status_code == 401


def test_store_rejects_unknown_kind(client):
    resp = _upload(client, "not-a-kind", "1")
    assert resp.status_code == 400


def test_get_rejects_unknown_kind(client):
    resp = client.get("/asset/not-a-kind/1")
    assert resp.status_code == 400


def test_get_missing_asset_404s(client):
    resp = client.get("/asset/avatar/does-not-exist")
    assert resp.status_code == 404


def test_store_then_get_round_trip(client):
    store_resp = _upload(client, "avatar", "1", data=b"pixel-data")
    assert store_resp.status_code == 201
    assert store_resp.headers["Location"] == "/asset/avatar/1"

    get_resp = client.get("/asset/avatar/1")
    assert get_resp.status_code == 200
    assert get_resp.data == b"pixel-data"


def test_get_is_served_from_cache_after_overwrite_is_invalidated(client):
    _upload(client, "avatar", "1", data=b"first")
    assert client.get("/asset/avatar/1").data == b"first"

    _upload(client, "avatar", "1", data=b"second")
    assert client.get("/asset/avatar/1").data == b"second"
