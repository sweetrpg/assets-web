# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""
"""

from functools import wraps
from sweetrpg_assets_web.application import constants
from sweetrpg_assets_web import __version__
from flask import Blueprint, request, session, jsonify, current_app, make_response, send_file, send_from_directory, abort, render_template
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from markupsafe import escape
from io import BytesIO
import mimetypes
from pathlib import Path
from sweetrpg_assets_web.application.cache import cache
from sweetrpg_assets_web.application import reclaim
from sweetrpg_assets_web.application import shared_session
import analytics
import datetime
import hmac
import json
import os
import redis
import requests


blueprint = Blueprint("web", __name__, template_folder="../templates")


def _render_maintenance_page(mode):
    window = ""
    if mode.starts_at or mode.ends_at:
        parts = []
        if mode.starts_at:
            parts.append(f"<strong>Starts:</strong> {escape(mode.starts_at)}")
        if mode.ends_at:
            parts.append(f"<strong>Ends:</strong> {escape(mode.ends_at)}")
        window = f'<p class="window">{" &middot; ".join(parts)}</p>'

    html = render_template(
        "maintenance.html",
        label=mode.label if mode.label else "Under Maintenance",
        description=mode.description if mode.description else "",
        window=window,
        logo_url=f"{current_app.config['SHARED_URL']}/static/img/assets/logo.svg",
        favicon_url=f"{current_app.config['SHARED_URL']}/static/img/assets/favicon.png",
    )
    return make_response(html, 503, {"Content-Type": "text/html", "Retry-After": "120"})


# Health checks must stay reachable during maintenance, or orchestration (k8s liveness/readiness
# probes) sees the pod as unhealthy and restarts/removes it from service instead of just serving
# the maintenance page. `health_blueprint` is registered as a nested blueprint on `blueprint`
# ("web"), so its routes report `request.blueprint == "web.health"`.
_HEALTH_BLUEPRINT_NAME = "web.health"


@blueprint.before_request
def _check_maintenance_mode():
    current_app.logger.info("check_maintenance_mode", extra={"path": request.path})

    if request.blueprint == _HEALTH_BLUEPRINT_NAME or request.path.startswith("/health/"):
        return None

    admin_client = getattr(current_app, "admin_client", None)
    if admin_client is None:
        return None

    try:
        modes = admin_client.fetch_maintenance_modes(constants.MAINTENANCE_MODE_SCOPES)
    except Exception:
        # The SDK's own contract is fail-open (never raises), but don't let a bug in this
        # integration point itself take the whole app down - fall through to normal rendering.
        current_app.logger.exception("Failed to check maintenance mode; rendering normally")
        return None

    if not modes:
        return None

    return _render_maintenance_page(modes[0])


@blueprint.before_request
def _populate():
    current_app.logger.debug("session: %s", session)
    current_app.logger.debug("headers: %s", request.headers)
    current_app.logger.debug("cookies: %s", request.cookies)
    current_app.logger.debug("args: %s", request.args)

    userinfo = None
    if constants.PROFILE_KEY in session:
        userinfo = session[constants.PROFILE_KEY]
    elif constants.SWEETRPG_AUTH_KEY in request.cookies:
        userinfo = request.cookies[constants.SWEETRPG_AUTH_KEY]
        session[constants.PROFILE_KEY] = userinfo

    # Read the suite-wide login session directly (see shared_session.py) rather than trusting
    # X-Forwarded-* headers from an upstream auth proxy - no such proxy has ever been wired up
    # in front of this app, so those headers were always empty and every authenticated write
    # 401'd unconditionally.
    user = shared_session.current_user()
    session[constants.SESSION_ACCESS_TOKEN] = user.get("accessToken") if user else None
    session[constants.SESSION_EMAIL] = user.get("email") if user else None
    session[constants.SESSION_USER_ID] = user.get("sub") if user else None

    current_app.logger.debug("(updated) session: %s", session)
    current_app.logger.debug("userinfo: %s", userinfo)


@blueprint.before_request
def _store_user():
    current_app.logger.debug("store_user: session: %s", session)

    email = session.get(constants.SESSION_EMAIL)
    current_app.logger.debug("email: %s", email)
    user_id = session.get(constants.SESSION_USER_ID)
    current_app.logger.debug("user_id: %s", user_id)
    if user_id and email:
        # TODO: store user
        pass


@blueprint.before_request
def _track():
    # analytics.identify/track raise AssertionError if write_key isn't configured - without
    # this guard, every authenticated request 500s in any environment that hasn't set
    # SEGMENT_WRITE_KEY.
    if not analytics.write_key:
        return

    email = session.get(constants.SESSION_EMAIL)
    current_app.logger.debug("email: %s", email)
    user_id = session.get(constants.SESSION_USER_ID)
    current_app.logger.debug("user_id: %s", user_id)
    if user_id and email:
        analytics.identify(user_id, {"email": email, "created_at": datetime.datetime.now()})

        analytics.track(user_id, request.full_path, {"user_agent": request.headers.get("User-Agent")})


@blueprint.errorhandler(Exception)
def error_handler(ex):
    current_app.logger.exception("Exception caught: %s", ex)
    response = jsonify(message=str(ex))
    response.status_code = ex.code if isinstance(ex, HTTPException) else 500
    return response


def _load_build_info():
    try:
        with open(current_app.config["BUILD_INFO_PATH"]) as f:
            info = json.load(f)
            # Matches catalog-web/main-web's convention of an 8-char short sha - Python's
            # string slicing is a safe no-op on a shorter string, unlike Askama's build_hash[..8]
            # which panicked on one (see main-web's routes/main.rs comment).
            return info.get("date", "unknown"), info.get("sha", "unknown")[:8]
    except Exception:
        return "unknown", "unknown"


# Assets are fetched by kind and ID known from other services (e.g. a catalog entry's image
# reference), not browsed - this is a static placeholder, not a real landing page.
@blueprint.route("/")
def main_page():
    current_app.logger.info("main_page")
    build_timestamp, build_hash = _load_build_info()
    return render_template(
        "main.html",
        root_url=current_app.config["ROOT_URL"],
        logo_url=f"{current_app.config['SHARED_URL']}/static/img/assets/logo.png",
        favicon_url=f"{current_app.config['SHARED_URL']}/static/img/assets/favicon.png",
        version=__version__,
        build_timestamp=build_timestamp,
        build_hash=build_hash,
    )


# Preference order when more than one image type exists for the same id - checked first to
# last, first match wins.
IMAGE_TYPES = ['svg', 'webp', 'png', 'jpg', 'jpeg', 'gif']


def _validated_kind_id(kind: str, id: str) -> tuple[str, str]:
    """Rejects a kind outside the fixed ALLOWED_KINDS allowlist and an id that doesn't survive
    `secure_filename` unchanged (path traversal, empty, or otherwise unsafe)."""
    _require_known_kind(kind)

    safe_id = secure_filename(id)
    if not safe_id or safe_id != id:
        abort(400, description="Invalid asset id")

    return kind, safe_id


def _asset_dir(kind: str, id: str) -> Path:
    """The directory an asset's id is stored under - `base/<kind>/<id>/`, holding one or more
    `image.<ext>` files. Doesn't require the directory to already exist - callers that need an
    existing asset (GET) should use `_asset_path` instead, which resolves to a specific file."""
    safe_kind, safe_id = _validated_kind_id(kind, id)
    base = Path(current_app.config["ASSET_DATA_PATH"]).resolve()
    return (base / safe_kind / safe_id).resolve()


def _asset_path(kind: str, id: str) -> Path:
    """Resolve the on-disk path of an existing asset's image file, preferring `IMAGE_TYPES`'
    order when more than one type is present. 404s if no `_asset_dir(kind, id)` has any."""
    current_app.logger.debug("_asset_path: kind=%s id=%s", kind, id)

    directory = _asset_dir(kind, id)
    current_app.logger.debug("_asset_path: directory=%s", directory)

    for image_type in IMAGE_TYPES:
        current_app.logger.debug("_asset_path: image_type=%s", image_type)
        candidate = directory / f'image.{image_type}'
        if candidate.exists():
            current_app.logger.debug("_asset_path: candidate=%s", candidate)
            return candidate

    abort(404, description=f"No asset found of any type for id {id}")


def _require_known_kind(kind: str) -> None:
    if kind not in constants.ALLOWED_KINDS:
        abort(400, description=f"Unknown asset kind: {kind}")


def _require_authenticated() -> None:
    if not (session.get(constants.SESSION_USER_ID) and session.get(constants.SESSION_EMAIL)):
        abort(401, description="Authentication required")


def _require_valid_upload(upload) -> None:
    if upload.mimetype not in constants.ALLOWED_CONTENT_TYPES:
        abort(400, description=f"Unsupported content type: {upload.mimetype}")

    upload.stream.seek(0, 2)
    size = upload.stream.tell()
    upload.stream.seek(0)
    if size > constants.MAX_ASSET_UPLOAD_BYTES:
        abort(400, description="File exceeds maximum upload size")


def _cache_key(kind: str, id: str) -> str:
    return f"asset:{kind}:{id}"


@blueprint.route("/asset/<kind>/<id>", methods=['GET'])
def get_asset(kind: str, id: str):
    current_app.logger.info("get_asset", extra={"kind": kind, "id": id})

    _require_known_kind(kind)

    cache_key = _cache_key(kind, id)
    cached = cache.get(cache_key)
    if cached is not None:
        data, mimetype = cached
        return send_file(BytesIO(data), mimetype=mimetype)

    path = _asset_path(kind, id)
    if not path.is_file():
        abort(404, description=f"Asset not found for id {id}")

    data = path.read_bytes()
    mimetype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    current_app.logger.info("store_asset: setting cache key", extra={"kind": kind, "id": id, "cache_key": cache_key})
    cache.set(cache_key, (data, mimetype), timeout=current_app.config["ASSET_CACHE_TTL"])

    return send_file(BytesIO(data), mimetype=mimetype)


@blueprint.route("/asset/<kind>/<id>", methods=['POST'])
def store_asset(kind: str, id: str):
    current_app.logger.info("store_asset", extra={"kind": kind, "id": id})

    _require_authenticated()
    _require_known_kind(kind)

    upload = request.files.get("file")
    if upload is None or not upload.filename:
        abort(400, description="No file provided")
    _require_valid_upload(upload)

    asset_dir = _asset_dir(kind, id)
    asset_dir.mkdir(parents=True, exist_ok=True)

    # A re-upload replaces whatever image type was there before - otherwise a cover changed
    # from .png to .jpg would leave the stale .png behind, and IMAGE_TYPES' priority order
    # would keep serving it instead of the new upload.
    for image_type in IMAGE_TYPES:
        (asset_dir / f'image.{image_type}').unlink(missing_ok=True)

    _, filename_ext = os.path.splitext(upload.filename)
    file_path = asset_dir / f'image{filename_ext}'
    upload.save(file_path)

    # Invalidate rather than repopulate - the next GET will read the new file and refill the
    # cache with the correct content, avoiding a race with a GET that's mid-flight right now.
    current_app.logger.info("store_asset: invalidating cache", extra={"kind": kind, "id": id})
    cache.delete(_cache_key(kind, id))

    response = jsonify(kind=kind, id=id)
    response.status_code = 201
    response.headers["Location"] = f"/asset/{kind}/{id}"
    return response


@blueprint.route("/asset/<kind>/<id>", methods=['DELETE'])
def delete_asset(kind: str, id: str):
    current_app.logger.info("delete_asset", extra={"kind": kind, "id": id})

    _require_authenticated()
    _require_known_kind(kind)

    path = _asset_dir(kind, id)
    if not path.is_dir():
        abort(404, description="Asset not found")

    for file in path.iterdir():
        current_app.logger.info("delete_asset: deleting asset file", extra={"kind": kind, "id": id, "file": file.name})
        file.unlink(missing_ok=True)
    current_app.logger.info("delete_asset: deleting asset directory", extra={"kind": kind, "id": id})
    path.rmdir()

    current_app.logger.info("store_asset: invalidating cache", extra={"kind": kind, "id": id})
    cache.delete(_cache_key(kind, id))

    response = jsonify(kind=kind, id=id)
    response.status_code = 204
    return response


def _require_reclaim_token() -> None:
    expected = current_app.config.get("RECLAIM_JOB_TOKEN")
    if not expected:
        abort(503, description="Reclaim job is not configured")

    presented = request.headers.get("X-Reclaim-Token", "")
    if not hmac.compare_digest(presented, expected):
        abort(401, description="Invalid reclaim token")


@blueprint.route("/admin/reclaim-staged-assets", methods=["POST"])
def reclaim_staged_assets():
    """Triggered by a Kubernetes CronJob (see kubernetes/base/reclaim-cronjob.yaml), not a
    user - see reclaim.py's docstring for what "orphaned" means and why the check is two-part."""
    current_app.logger.info("reclaim_staged_assets")

    _require_reclaim_token()

    try:
        deleted = reclaim.reclaim_staged_assets()
    except (RuntimeError, requests.exceptions.RequestException, redis.exceptions.RedisError) as ex:
        current_app.logger.exception("reclaim_staged_assets: dependency unavailable")
        abort(503, description=str(ex))

    current_app.logger.info("reclaim_staged_assets: done", extra={"deleted_count": len(deleted)})
    return jsonify(deleted=deleted)


from sweetrpg_web_core.blueprints import health
