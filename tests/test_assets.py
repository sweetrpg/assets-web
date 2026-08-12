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


def test_store_rejects_oversized_upload(client):
    oversized = b"x" * (5 * 1024 * 1024 + 1)
    resp = _upload(client, "avatar", "1", data=oversized)
    assert resp.status_code == 400


def test_store_accepts_upload_at_max_size(client):
    max_size = b"x" * (5 * 1024 * 1024)
    resp = _upload(client, "avatar", "1", data=max_size)
    assert resp.status_code == 201


def test_store_rejects_unsupported_content_type(client):
    resp = _upload(client, "avatar", "1", filename="a.pdf", data=b"not an image")
    assert resp.status_code == 400


def test_store_accepts_every_allowed_kind(client):
    for kind in ("avatar", "map", "token", "portrait", "cover", "cover-staged", "sample-staged"):
        resp = _upload(client, kind, "1", data=b"pixels")
        assert resp.status_code == 201, kind


def test_delete_requires_authentication(client):
    _upload(client, "avatar", "1")
    resp = client.delete("/asset/avatar/1", headers={})
    assert resp.status_code == 401


def test_delete_rejects_unknown_kind(client):
    resp = client.delete("/asset/not-a-kind/1", headers=AUTH_HEADERS)
    assert resp.status_code == 400


def test_delete_missing_asset_404s(client):
    resp = client.delete("/asset/avatar/does-not-exist", headers=AUTH_HEADERS)
    assert resp.status_code == 404


def test_delete_removes_asset_and_invalidates_cache(client):
    _upload(client, "cover-staged", "1", data=b"staged-bytes")
    assert client.get("/asset/cover-staged/1").data == b"staged-bytes"

    delete_resp = client.delete("/asset/cover-staged/1", headers=AUTH_HEADERS)
    assert delete_resp.status_code == 204

    get_resp = client.get("/asset/cover-staged/1")
    assert get_resp.status_code == 404


def test_cover_kind_round_trip(client):
    # catalog-web's volume cover images (expand-volume-detail-page) - a separate kind from
    # `portrait` so book covers don't share a namespace with character portrait art.
    store_resp = _upload(client, "cover", "volume-1", data=b"cover-bytes")
    assert store_resp.status_code == 201

    get_resp = client.get("/asset/cover/volume-1")
    assert get_resp.status_code == 200
    assert get_resp.data == b"cover-bytes"
