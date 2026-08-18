# AGENTS.md

This file provides guidance to Claude Code, Codex, GitHub Copilot, and other coding agents
working in this repository.

## About This Project

`assets-web` is a Flask service that stores and serves the SweetRPG platform's binary assets
(avatars, maps, tokens, portraits). `GET /asset/<kind>/<id>` fetches one; `POST
/asset/<kind>/<id>` (authenticated) uploads one. It's the org's first Python
**web frontend** to get the full observability treatment (tracing/JSON logs/metrics/rate
limiting) - there's no `docs/service-conventions.md`-equivalent for Python yet (that doc is
explicitly Go-specific and says to write the convention up once a second Python service exists
to compare against - not yet), so the choices below are this repo's own, not a platform-wide
standard.

### Asset storage model

- Files live under `ASSET_DATA_PATH` (default `/data`, mounted from a `ReadWriteMany` PVC -
  required because the HPA runs 2-10 replicas that all need the same files, not each their own
  copy).
- `kind` is validated against a fixed allowlist (`constants.ALLOWED_KINDS`) - a typo or an
  unexpected value gets a 400, not a silently-created new directory.
- `id` is passed through `secure_filename` and rejected (400) if that changes it - blocks path
  traversal.
- `GET` is cache-aside: checks Redis first (`asset:<kind>:<id>`, file bytes + mimetype, TTL
  `ASSET_CACHE_TTL`), falls through to disk on a miss and repopulates. `POST` invalidates rather
  than repopulates, so a GET racing a POST reads the new file, not stale cached bytes from before
  the write landed.
- `POST` requires an authenticated session (`session[user_id]`/`session[email]` both set - see
  `_populate` in `blueprints/__init__.py`, populated from `X-Forwarded-User`/`X-Forwarded-Email`
  set by the upstream auth proxy, not validated by this app itself) - 401 otherwise.

### Shared static assets

The platform's shared branding (logo, favicon, stylesheet) moved to `shared-web` - this repo no
longer hosts a `/static/<path:filename>` route or checked-in branding files (see
`docs/frontend-conventions.md` in `sweetrpg/platform`). This app's own `/` landing page and
maintenance-mode page link to their logo/favicon via `SHARED_URL` (config default
`http://localhost:8081`, set to `shared-web`'s address in each `kubernetes/overlays/*`
configmap) - e.g. `{SHARED_URL}/static/img/assets/logo.png`.

### Known gaps fixed while building this

Several were live bugs, not stylistic nits - worth knowing about if you're wondering why the
code looks different from git blame around it:

- `application/__init__.py` used to call `sentry_sdk.init()` unconditionally at **module import
  time**, using `os.environ[SENTRY_DSN]` - `KeyError` if unset, crashing before the app could
  even start. Removed; `main.py`'s `create_app()` already does the correct conditional Sentry
  setup (`if not app.debug`).
- `config.py`'s `DEBUG` was `bool(os.environ.get("DEBUG") or True)` - any non-empty string
  (including `"false"`) is truthy, so this was always `True` regardless of the actual env var.
  Fixed via a real boolean parse (`_env_bool`).
- `main.py` set `app.debug` from `app.config` **before** calling `app.config.from_object(...)` -
  read Flask's pre-config default, not the real value. Reordered.
- `blueprints/__init__.py`'s `_track()` before-request hook called `analytics.identify(...)`
  unconditionally whenever a user was in session - Segment's client raises `AssertionError` if
  `write_key` isn't configured, so every authenticated request 500'd in any environment without
  `SEGMENT_WRITE_KEY` set. Now guarded.
- The `redis` package itself was never a listed dependency anywhere (only `hiredis`, its C parser
  accelerator - not a substitute) despite `config.py`/`main.py` importing it directly. Added.
- `main_blueprint` is a module-level singleton; registering `health_blueprint` onto it twice
  (e.g. `create_app()` called more than once in one process - tests, a REPL) raises `AssertionError`
  in Flask 3.x. Guarded with `main_blueprint._got_registered_once`.

## Observability

- **Logging**: `python-json-logger` (`pythonjsonlogger.json.JsonFormatter`, not the deprecated
  `pythonjsonlogger.jsonlogger` path - `setup.cfg` has `filterwarnings = error`, which turns that
  module's `DeprecationWarning` into a test failure). One JSON object per line to stdout.
- **Tracing**: `application/tracing.py`, OTLP/HTTP to `OTEL_EXPORTER_OTLP_ENDPOINT` (Tempo). The
  tracer provider is created once and lives for the process's lifetime - see that file's own
  comment for why: catalog-api shipped a bug where a misplaced `defer` shut its tracer down
  within milliseconds of startup, silently dropping every span. Don't repeat the shape here.
- **Metrics**: `application/metrics.py`, `prometheus-flask-exporter` at `/metrics`, scraped via
  the `PodMonitor` in `kubernetes/overlays/dev/pod-monitor.yaml`.
- **Rate limiting**: `application/limiter.py`, Flask-Limiter with a constant key function (one
  shared bucket for every client and route, not per-client) - matches the Go services'
  `golang.org/x/time/rate` convention. Limit string from `RATE_LIMIT`.
- **Caching**: `application/cache.py` (flask-caching + Redis), used by the asset GET path (see
  above).

## Committing Code

[Conventional Commits](https://www.conventionalcommits.org/): `<type>(<scope>): <description>`.

## Branches and Workflow

Git-flow (see `docs/git-flow.md` in `sweetrpg/platform`): `develop` is the integration branch,
`master` reflects the latest release. Feature/fix branches off `develop`, PR back into `develop`.

Releasing: dispatch the "Prepare Release" workflow - it computes the next version via
`git-cliff`, bumps `__version__` in `src/sweetrpg_assets_web/__init__.py`, updates
`CHANGELOG.md`, and opens a `release/<version>` PR into `master`. Merging that PR tags the
release, which builds and pushes the Docker image and bumps the deployed image tag in
`sweetrpg/kubernetes` automatically (`.github/workflows/prepare-release.yaml`/`release.yaml`/
`tag-release.yaml`, using the `sweetrpg/github-actions` reusable Python release workflow family -
this repo is its first consumer). Previously this repo had no real release workflow at all: a
`relekang/python-semantic-release` step auto-tagged every `develop` push directly, with no
review step and no changelog - removed in favor of the above.

## Running Checks Locally

Python 3.14, managed via [uv](https://docs.astral.sh/uv/) rather than pip/pip-tools directly -
`uv` replaces pip-tools' `pip-compile` (see `scripts/update-requirements.sh`) and is the install
tool for both local dev and CI. `tox` still drives the actual test run, but with `tox.ini`'s
`runner = uv-venv-runner` (from the `tox-uv` plugin, listed in `requirements/tests.in`) it
creates environments and installs dependencies through `uv` instead of `virtualenv`/`pip` -
`tox-uv` doesn't take over just by being installed; the `runner` setting is what opts in.

```bash
uv venv --python 3.14
source .venv/bin/activate
uv pip install -r requirements/tests.txt -e .
python -m pytest tests
```

Requires a local Redis (`redis-server` on `localhost:6379`, no auth needed) - used for caching,
sessions, and rate limiting. Set `ASSET_DATA_PATH` to a scratch directory for local runs; it
defaults to `/data`, which won't exist outside the container.
