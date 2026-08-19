# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""reclaim.py

Periodic reclaim of orphaned cover-staged/sample-staged assets (durable-volume-editing task
2.4). A staged asset can legitimately outlive its edit session (a submitter's finalize hands
the reference to a pending submission), so an asset is only ever deleted when NEITHER of two
independent sources still claims it: the edit-session store (a live session) and catalog-api
(a pending submission awaiting review). Both checks must succeed for a run to delete anything -
see reclaim_staged_assets's docstring.
"""

import json
from pathlib import Path

import redis
import requests
from flask import current_app

from sweetrpg_assets_web.application.cache import cache

STAGED_KINDS = ("cover-staged", "sample-staged")


def _cache_key(kind: str, id: str) -> str:
    return f"asset:{kind}:{id}"


def _list_staged_ids(kind: str) -> list[str]:
    base = Path(current_app.config["ASSET_DATA_PATH"]).resolve() / kind
    if not base.is_dir():
        return []
    return [p.name for p in base.iterdir() if p.is_dir()]


def _delete_staged_asset(kind: str, id: str) -> None:
    base = Path(current_app.config["ASSET_DATA_PATH"]).resolve()
    path = base / kind / id
    for file in path.iterdir():
        file.unlink(missing_ok=True)
    path.rmdir()
    cache.delete(_cache_key(kind, id))


def _staged_owner_id(kind: str, asset_id: str) -> str:
    """The edit-session owner for a staged asset id. `cover-staged` ids are the bare userId
    (`cover-staged/<userId>`); `sample-staged` ids append an index
    (`sample-staged/<userId>-<n>`)."""
    if kind == "cover-staged":
        return asset_id
    return asset_id.rsplit("-", 1)[0]


def _edit_session_client() -> redis.Redis:
    host = current_app.config.get("EDIT_SESSION_REDIS_HOST")
    if not host:
        raise RuntimeError("EDIT_SESSION_REDIS_HOST is not configured")
    return redis.Redis(
        host=host,
        port=current_app.config["EDIT_SESSION_REDIS_PORT"],
        db=current_app.config["EDIT_SESSION_REDIS_DB"],
        decode_responses=True,
    )


def _sanitized_user_id(sub: str) -> str:
    """Mirrors catalog-web's `sanitizedAssetUserID` (EditReviewFunctions.swift): a raw Auth0
    subject (e.g. `auth0|abc123`) isn't a valid assets-web id, so staged asset ids are filed
    under this sanitized form. Session keys are stored under the raw, unsanitized sub - so
    matching a staged asset id back to its owning session requires sanitizing each session
    key's owner segment the same way, not sanitizing the owner_id backwards."""
    return sub.replace("|", "-")


def _referenced_by_live_session(client: redis.Redis, owner_id: str, asset_id: str, is_cover: bool) -> bool:
    for key in client.scan_iter(match="edit-session:*:*"):
        key_owner = key.split(":")[1]
        if _sanitized_user_id(key_owner) != owner_id:
            continue
        raw = client.get(key)
        if not raw:
            continue
        session = json.loads(raw)
        if is_cover:
            if session.get("stagedCoverAssetId") == asset_id:
                return True
        elif asset_id in (session.get("sampleAssetIds") or []):
            return True
    return False


def _fetch_pending_staged_ids() -> tuple[set[str], set[str]]:
    base_url = current_app.config.get("CATALOG_API_URL")
    if not base_url:
        raise RuntimeError("CATALOG_API_URL is not configured")
    resp = requests.get(f"{base_url}/staged-assets/pending", timeout=10)
    resp.raise_for_status()
    body = resp.json()
    return set(body.get("coverAssetIds") or []), set(body.get("sampleAssetIds") or [])


def reclaim_staged_assets() -> list[str]:
    """Deletes every cover-staged/sample-staged asset that neither a live edit session nor a
    pending catalog-api submission references. Fails safe: a RuntimeError/request error from
    either check propagates and aborts the whole run before anything is deleted, rather than
    treating an unreachable dependency as "not referenced".

    Returns the "<kind>/<id>" identifiers actually deleted.
    """
    pending_covers, pending_samples = _fetch_pending_staged_ids()
    session_client = _edit_session_client()

    deleted = []
    for kind, pending_ids in (("cover-staged", pending_covers), ("sample-staged", pending_samples)):
        is_cover = kind == "cover-staged"
        for asset_id in _list_staged_ids(kind):
            if asset_id in pending_ids:
                continue
            owner_id = _staged_owner_id(kind, asset_id)
            if _referenced_by_live_session(session_client, owner_id, asset_id, is_cover):
                continue
            _delete_staged_asset(kind, asset_id)
            deleted.append(f"{kind}/{asset_id}")

    return deleted
