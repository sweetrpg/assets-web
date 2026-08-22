# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""test_bearer_token.py
Tests for forwarded-bearer-token authentication on the asset store routes - the
service-to-service path (e.g. catalog-api promoting a staged cover) that carries no browser
session cookie. See sweetrpg/platform's api-client-auth change.
"""

import io
import time

import jwt as pyjwt
from conftest import authenticate as _authenticate
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
from sweetrpg_assets_web.application import bearer_token

DOMAIN = "test-tenant.auth0.com"
AUDIENCE = "https://sweetrpg.com/api/"


def _make_key(monkeypatch):
    """Generates an RSA keypair and points the module's JWKS client at it, so tokens signed by
    the private key verify without touching a real Auth0 tenant."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json_public = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    jwk["kid"] = "test-key"
    jwk["alg"] = "RS256"
    jwk["use"] = "sig"

    class _FakeJWKSClient:
        def get_signing_key_from_jwt(self, token):
            class _Key:
                key = private_key.public_key()

            return _Key()

    monkeypatch.setitem(bearer_token._jwks_clients, DOMAIN, _FakeJWKSClient())
    del json_public
    return private_key


def _token(app, private_key, **overrides):
    claims = {
        "sub": "github|419457",
        "iss": f"https://{DOMAIN}/",
        "aud": AUDIENCE,
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
    }
    claims.update(overrides)
    if "exp" in overrides and overrides["exp"] is None:
        del claims["exp"]
    return pyjwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})


def _configure(app, monkeypatch):
    monkeypatch.setitem(app.config, "AUTH0_DOMAIN", DOMAIN)
    monkeypatch.setitem(app.config, "AUTH0_AUDIENCE", AUDIENCE)


def test_bearer_upload_succeeds(app, client, monkeypatch):
    _configure(app, monkeypatch)
    private_key = _make_key(monkeypatch)

    resp = client.post(
        "/asset/avatar/svc-1",
        data={"file": (io.BytesIO(b"pixels"), "a.png")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {_token(app, private_key)}"},
    )
    assert resp.status_code == 201


def test_expired_bearer_rejected(app, client, monkeypatch):
    _configure(app, monkeypatch)
    private_key = _make_key(monkeypatch)

    resp = client.post(
        "/asset/avatar/svc-2",
        data={"file": (io.BytesIO(b"pixels"), "a.png")},
        content_type="multipart/form-data",
        headers={
            "Authorization": f"Bearer {_token(app, private_key, exp=int(time.time()) - 10)}"
        },
    )
    assert resp.status_code == 401


def test_wrong_audience_rejected(app, client, monkeypatch):
    _configure(app, monkeypatch)
    private_key = _make_key(monkeypatch)

    resp = client.post(
        "/asset/avatar/svc-3",
        data={"file": (io.BytesIO(b"pixels"), "a.png")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {_token(app, private_key, aud='https://other.api/')}"},
    )
    assert resp.status_code == 401


def test_garbage_bearer_rejected(app, client, monkeypatch):
    _configure(app, monkeypatch)
    _make_key(monkeypatch)

    resp = client.post(
        "/asset/avatar/svc-4",
        data={"file": (io.BytesIO(b"pixels"), "a.png")},
        content_type="multipart/form-data",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert resp.status_code == 401


def test_unconfigured_tenant_fails_closed_per_request(app, client, monkeypatch):
    # No AUTH0_DOMAIN/AUTH0_AUDIENCE configured: no bearer auth happens, and unlike a bad token
    # this must not take the app down - the request just reads as unauthenticated.
    _make_key(monkeypatch)

    resp = client.post(
        "/asset/avatar/svc-5",
        data={"file": (io.BytesIO(b"pixels"), "a.png")},
        content_type="multipart/form-data",
        headers={"Authorization": "Bearer whatever"},
    )
    assert resp.status_code == 401


def test_session_cookie_still_authenticates(client):
    # The bearer path is additive - browser sessions keep working unchanged.
    _authenticate(client)
    resp = client.post(
        "/asset/avatar/browser-1",
        data={"file": (io.BytesIO(b"pixels"), "a.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201
