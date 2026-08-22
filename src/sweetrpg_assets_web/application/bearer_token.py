# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""bearer_token.py

Validation of Auth0-issued user access tokens forwarded as `Authorization: Bearer` by
first-party services acting on a user's behalf - e.g. catalog-api promoting a staged cover to
live during edit-session finalize. Server-to-server calls carry no browser session cookie, so
the shared-session lookup in shared_session.py can't authenticate them; the forwarded token is
the platform's one authorization path for every caller (see sweetrpg/platform's api-client-auth
change, and its api-token-validation spec: verify signature/exp/iss/aud, reject otherwise).

The tenant's JWKS is fetched on first use and cached; an unknown signing `kid` triggers exactly
one refetch before failing, so key rotation doesn't produce a window of spurious 401s.

Fails closed on any invalid token (returns None), but fails open on configuration gaps the same
way shared_session does: with AUTH0_DOMAIN/AUTH0_AUDIENCE unset this client returns None for
every request rather than taking the app down.
"""

import logging
from typing import Any

import jwt
from flask import current_app, request
from jwt import PyJWKClient


def current_user_from_bearer() -> dict[str, Any] | None:
    """Returns {sub, email?} decoded from a valid forwarded bearer token, or None.

    Requires both AUTH0_DOMAIN and AUTH0_AUDIENCE configured; iss must match the tenant and aud
    must contain the platform API audience, matching auth-api's own verification contract.
    """
    domain = current_app.config.get("AUTH0_DOMAIN")
    audience = current_app.config.get("AUTH0_AUDIENCE")
    if not domain or not audience:
        return None

    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header[len("Bearer "):].strip()
    if not token:
        return None

    jwks_client = _jwks_client(domain)
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=f"https://{domain}/",
        )
    except Exception:
        logging.exception("bearer_token: rejected forwarded token")
        return None

    return {"sub": claims.get("sub"), "email": claims.get("email")}


_jwks_clients: dict[str, PyJWKClient] = {}


def _jwks_client(domain: str) -> PyJWKClient:
    # One client per domain caches that tenant's keys; the refetch-on-unknown-kid behavior is
    # PyJWKClient's default, which is all the rotation handling this needs.
    client = _jwks_clients.get(domain)
    if client is None:
        client = PyJWKClient(f"https://{domain}/.well-known/jwks.json", cache_keys=True)
        _jwks_clients[domain] = client
    return client
