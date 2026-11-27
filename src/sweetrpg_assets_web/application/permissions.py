# -*- coding: utf-8 -*-
"""permissions.py

Who may write or delete an asset. Roles come from auth-api's `POST /authz/check` with the
caller's own token (PADR-0037), never from the session's login-time copy. Anything other than a
well-formed answer denies the request.
"""

__author__ = "Paul Schifferer <dm@sweetrpg.com>"


import requests
from flask import abort, current_app

from sweetrpg_assets_web.application import constants
from sweetrpg_assets_web.application.reclaim import STAGED_KINDS, _sanitized_user_id


REVIEWER_ROLES = frozenset({"editor", "admin"})


def _caller_roles(token: str) -> set[str]:
    """Returns the caller's current roles, aborting with 401/403/503 if they aren't available."""
    base_url = current_app.config.get("AUTH_API_URL")
    if not base_url:
        current_app.logger.error("AUTH_API_URL is not configured")
        abort(503, description="Authorization is unavailable")

    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/authz/check",
            json={"service": constants.AUTHZ_SERVICE_NAME},
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
            allow_redirects=False,
        )
        status = response.status_code
        body = response.json() if status == 200 else None
    except (requests.exceptions.RequestException, ValueError) as ex:
        current_app.logger.error("authz check failed: %s", type(ex).__name__)
        abort(503, description="Authorization is unavailable")

    if status == 401:
        abort(401, description="Authentication required")
    if isinstance(body, dict) and body.get("allowed") is False:
        abort(403, description="Not permitted")
    if not isinstance(body, dict) or body.get("allowed") is not True or not isinstance(body.get("roles"), list):
        current_app.logger.error("authz check returned an unusable response", extra={"status": status})
        abort(503, description="Authorization is unavailable")

    return {role for role in body["roles"] if isinstance(role, str)}


def _owns_staged_asset(sub: str, kind: str, asset_id: str) -> bool:
    """Staged ids are `cover-staged/<owner>` and `sample-staged/<owner>-<n>`, where owner is the
    sanitized subject (catalog-web's `sanitizedAssetUserID`)."""
    owner = asset_id
    if kind == "sample-staged":
        owner, separator, index = asset_id.rpartition("-")
        if not separator or not index.isdecimal():
            return False
    return owner == _sanitized_user_id(sub)


def require_asset_permission(user: dict, kind: str, asset_id: str, *, deleting: bool) -> None:
    """Published kinds need editor/admin. Staged kinds are writable only by their owner;
    editor/admin may also delete them, because accepting a submission promotes the submitter's
    staged asset with the reviewer's token."""
    token = user.get("accessToken")
    if not token:
        abort(401, description="Authentication required")

    roles = _caller_roles(token)

    if kind in STAGED_KINDS:
        if _owns_staged_asset(user["sub"], kind, asset_id):
            return
        if deleting and roles & REVIEWER_ROLES:
            return
    elif roles & REVIEWER_ROLES:
        return

    abort(403, description="Not permitted")
