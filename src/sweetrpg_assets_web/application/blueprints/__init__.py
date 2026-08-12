# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""
"""

from functools import wraps
from sweetrpg_assets_web.application import constants
from sweetrpg_assets_web import __version__
from flask import Blueprint, request, session, jsonify, current_app, make_response, send_file, send_from_directory, abort, url_for, render_template
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from markupsafe import escape
from io import BytesIO
import mimetypes
from pathlib import Path
from sweetrpg_assets_web.application.cache import cache
import analytics
import datetime
import json


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
        logo_url=url_for("web.static_asset", filename="img/assets/logo.svg"),
        favicon_url=url_for("web.static_asset", filename="img/assets/favicon.png"),
    )
    return make_response(html, 503, {"Content-Type": "text/html", "Retry-After": "120"})


# Health checks must stay reachable during maintenance, or orchestration (k8s liveness/readiness
# probes) sees the pod as unhealthy and restarts/removes it from service instead of just serving
# the maintenance page. `health_blueprint` is registered as a nested blueprint on `blueprint`
# ("web"), so its routes report `request.blueprint == "web.health"`.
_HEALTH_BLUEPRINT_NAME = "web.health"


@blueprint.before_request
def _check_maintenance_mode():
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
    # Host: dev.sweetrpg.com
    # X-Real-Ip: 10.32.0.7
    # Connection: close
    # User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:93.0) Gecko/20100101 Firefox/93.0
    # Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8
    # Accept-Encoding: gzip, deflate, br
    # Accept-Language: en
    # Cookie: session=63e6f102-0b63-4576-9d1a-c9fdba16ba13; sweetrpg-auth=SrSVWUQeCGl_2cFbOQkyNS40zXOF1u4OJp0KJE3y-5sjr6mUviiCJda2Evrd375UMxg_ohwft_QgRyMlG8f3kY66WhVyKaIaAkBoYD1ruxexScFDL8whGg1-aOVs4v0PRoEPMcrMylacJ0-hhT_TgXGvHqFSyf5HuQb61R046oL2WztqEDnv4LFnXGWmDwzsmAtklz6jxZCuK8P0vWuWpLMdUkBHdwth-R2L1pSxscrH0SLLDA_mQPVpb6cHOTchNdxGMtp7CB79T87i8uB3jV1nHywexzg-ghj9_eHsRa_jH_hoc5wWsmzAzPW8cNWB_bfVh4I7sbMtYhSek5bSU4aZ3QuZJGHRKr3GJquEOzfrLf2MFrJj5VhH0bIXHKB6YqR9HRiJwJyySokiKropncqxVuuAQofd0vvNXd6lnL2R7E1Oq5_YkEzmZqvzMbylgn2TMZ6cRmnLagqnZade8LDG0TTFcGo3khP4SuDpgkx2q27uz7CiD6c-WxadwE8uxVnQ6tfSa7vrX9zXUtm44N9gZLGndQg4W0tj3nO2C8UwvjiMmAyUbQXA7GKDmPu3RZhoQ22y1IbKc0zN0zQP3YKNCSaIoeQoT1182Gtzj4EunIt-9eRAmGxKK0MBOHCH2Wq0rqLq5Sq9NdDILE8NkAq6SQHTl4CE_HeGpueq6QRmvZ6kFQJT9OxOrwRL0z6Y89SljFQ-5HeAyYvP3wqmlSW1aJ4nSBDP14xv-I_YpTW7KXaBFf2qSoxplGxSNyUVGD_PHl95vxYb4MycsILbkis6ivwMnwh4q1r32dZkg8tmhsocHUPwo1OS7OzD-K6DPmOXIOwfIZAAh2Mg179GG6u3DKYdsmQ2Tpv4tXnKm9AaryoT34T1vYDt2b4sLD8xXh0w8AMLwO88Q4sp2N6b0W4XAkHWadtUqIdDPdMHJQuam5fM1EFtQw6KPmeG1yasdGKaHk8drHrCltIcPpkXGC1Cwjs_gzDBxm2p68CkFZ7hlMXXbezIsLrNjwosGqNqgPrrk18KNjP2kmR1pfomQxTJF4AifAAAB6s4VsrKZT02FDlmJJP6AiKTtJNovVcrgoWld1WjrmZp3y4Jj1cWOhV7ZcAe7T7sjPlweBC1eIn9vlO5vDDDbIkaNqYvTtv3NOuwLQN2azmAt1_Vu6cpzYitZrlps80NzPNilWU-zI7caeIAFQBqX40bwBZXrUX88dIgJxNHCPePOBU6uM5Taddqk9cpKBzcG7T0pwF4XDTwhoTOkACqAtC26kwSwxuB2jSG6ZdXotsnTi-GnFaKZX6c6g0f_A44v_0AWch0PNV2v0AdSri9nMMBRkQ2HtkmoptV3LzvBpRkzZ0Boxfh0MafR4ugAWquNdxLlBJWATuTogmpiYdLPRw=|1635722526|tm8Zo044MaWFCyyO97ZD5VXPZJLfM9y1cKiC4NMYQ6Y=; ajs_anonymous_id=%2205a30181-160f-4a76-b562-7610a47369ea%22
    # Dnt: 1
    # Sec-Fetch-Dest: document
    # Sec-Fetch-Mode: navigate
    # Sec-Fetch-Site: none
    # Sec-Fetch-User: ?1
    # Upgrade-Insecure-Requests: 1
    # X-Forwarded-Access-Token: C99_j-whvVVd3AgQ--S1RCQC7tpTNgd7
    # X-Forwarded-Email: paul@schifferers.net
    # X-Forwarded-For: 10.46.0.0, 10.32.0.3
    # X-Forwarded-Host: dev.sweetrpg.com
    # X-Forwarded-Port: 80
    # X-Forwarded-Proto: http
    # X-Forwarded-Server: traefik-m5tc5
    # X-Forwarded-User: github|419457
    print(f"session: {session}")
    print(f"headers: {request.headers}")
    print(f"cookies: {request.cookies}")
    print(f"args: {request.args}")

    userinfo = None
    if constants.PROFILE_KEY in session:
        userinfo = session[constants.PROFILE_KEY]
    elif constants.SWEETRPG_AUTH_KEY in request.cookies:
        userinfo = request.cookies[constants.SWEETRPG_AUTH_KEY]
        session[constants.PROFILE_KEY] = userinfo
    session[constants.SESSION_ACCESS_TOKEN] = request.headers.get("X-Forwarded-Access-Token")
    session[constants.SESSION_EMAIL] = request.headers.get("X-Forwarded-Email")
    session[constants.SESSION_USER_ID] = request.headers.get("X-Forwarded-User")

    print(f"(updated) session: {session}")
    print(f"userinfo: {userinfo}")


@blueprint.before_request
def _store_user():
    email = session.get(constants.SESSION_EMAIL)
    print(f"email: {email}")
    user_id = session.get(constants.SESSION_USER_ID)
    print(f"user_id: {user_id}")
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
    print(f"email: {email}")
    user_id = session.get(constants.SESSION_USER_ID)
    print(f"user_id: {user_id}")
    if user_id and email:
        analytics.identify(user_id, {"email": email, "created_at": datetime.datetime.now()})

        analytics.track(user_id, request.full_path, {"user_agent": request.headers.get("User-Agent")})


@blueprint.errorhandler(Exception)
def error_handler(ex):
    current_app.logger.exception(f"Exception caught: {ex}")
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
    build_timestamp, build_hash = _load_build_info()
    return render_template(
        "main.html",
        root_url=current_app.config["SWEETRPG_ROOT_URL"],
        logo_url=url_for("web.static_asset", filename="img/assets/logo.png"),
        favicon_url=url_for("web.static_asset", filename="img/assets/favicon.png"),
        version=__version__,
        build_timestamp=build_timestamp,
        build_hash=build_hash,
    )


# Shared frontend branding (logo, favicon, stylesheet) checked into this repo and deployed with
# the app - distinct from the /asset/<kind>/<id> store below, which is authenticated, PVC-backed,
# user-uploaded content. No auth needed: these files are meant to be publicly embedded by any
# frontend.
_STATIC_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "static"


@blueprint.route("/static/<path:filename>")
def static_asset(filename: str):
    return send_from_directory(_STATIC_ASSETS_DIR, filename)


def _asset_path(kind: str, id: str) -> Path:
    """Resolve the on-disk path for an asset. Rejects a kind outside the fixed ALLOWED_KINDS
    allowlist and an id that doesn't survive `secure_filename` unchanged (path traversal,
    empty, or otherwise unsafe) - both checked here, in the same function that builds the
    path, rather than relying solely on callers to have validated kind first via
    `_require_known_kind`."""
    _require_known_kind(kind)
    allowed_kinds = {k: k for k in constants.ALLOWED_KINDS}
    safe_kind = allowed_kinds[kind]

    safe_id = secure_filename(id)
    if not safe_id or safe_id != id:
        abort(400, description="Invalid asset id")

    base = Path(current_app.config["ASSET_DATA_PATH"]).resolve()
    candidate = (base / safe_kind / safe_id).resolve()
    if candidate != base and base not in candidate.parents:
        abort(400, description="Invalid asset path")

    return candidate


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
    _require_known_kind(kind)

    cache_key = _cache_key(kind, id)
    cached = cache.get(cache_key)
    if cached is not None:
        data, mimetype = cached
        return send_file(BytesIO(data), mimetype=mimetype)

    path = _asset_path(kind, id)
    if not path.is_file():
        abort(404, description="Asset not found")

    data = path.read_bytes()
    mimetype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    cache.set(cache_key, (data, mimetype), timeout=current_app.config["ASSET_CACHE_TTL"])

    return send_file(BytesIO(data), mimetype=mimetype)


@blueprint.route("/asset/<kind>/<id>", methods=['POST'])
def store_asset(kind: str, id: str):
    _require_authenticated()
    _require_known_kind(kind)

    upload = request.files.get("file")
    if upload is None or not upload.filename:
        abort(400, description="No file provided")
    _require_valid_upload(upload)

    path = _asset_path(kind, id)
    path.parent.mkdir(parents=True, exist_ok=True)
    upload.save(path)

    # Invalidate rather than repopulate - the next GET will read the new file and refill the
    # cache with the correct content, avoiding a race with a GET that's mid-flight right now.
    cache.delete(_cache_key(kind, id))

    response = jsonify(kind=kind, id=id)
    response.status_code = 201
    response.headers["Location"] = f"/asset/{kind}/{id}"
    return response


@blueprint.route("/asset/<kind>/<id>", methods=['DELETE'])
def delete_asset(kind: str, id: str):
    _require_authenticated()
    _require_known_kind(kind)

    path = _asset_path(kind, id)
    if not path.is_file():
        abort(404, description="Asset not found")

    path.unlink()
    cache.delete(_cache_key(kind, id))

    response = jsonify(kind=kind, id=id)
    response.status_code = 204
    return response


from sweetrpg_web_core.blueprints import health
