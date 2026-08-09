# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""test_web.py
Tests for the main page and its reverse-proxy path-prefix handling.
"""

import json

from sweetrpg_assets_web.application.main import PrefixMiddleware


def test_main_page_links_are_unprefixed_by_default(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b'href="/static/css/page.css"' in resp.data
    assert b'src="/static/img/sweetrpg-logo-blueprint.png"' in resp.data


def test_main_page_links_are_prefixed_when_application_base_path_is_set(app):
    # Regression test: Traefik's strip-prefix Middleware removes /assets from PATH_INFO before
    # this app ever sees the request, so url_for() only emits the prefix if something wires
    # WSGI's SCRIPT_NAME into the environ (see PrefixMiddleware in main.py) - setting
    # APPLICATION_BASE_PATH in the configmap alone does nothing on its own, since it's an OS env
    # var, not part of the per-request WSGI environ uwsgi's --http mode builds.
    #
    # BaseConfig's values are read from os.environ at class-definition time (module import), not
    # per-request, so monkeypatching the env var and calling create_app() again wouldn't pick it
    # up once the config module has already been imported once in this test process. Wrapping
    # the existing app's wsgi_app directly exercises the same middleware without depending on
    # that ordering.
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, "/assets")
    client = app.test_client()

    resp = client.get("/")

    assert resp.status_code == 200
    assert b'href="/assets/static/css/page.css"' in resp.data
    assert b'src="/assets/static/img/sweetrpg-logo-blueprint.png"' in resp.data


def test_build_hash_is_truncated_to_8_chars(app, tmp_path):
    # Matches catalog-web (PageMeta.swift's buildHash: sha.prefix(8)) and main-web's own
    # 8-char convention - the full sha is far too long for the footer.
    build_info_path = tmp_path / "build-info.json"
    build_info_path.write_text(json.dumps({"date": "2026-08-09T00:00:00", "sha": "b38bd8e5d52aee04d6452fedb09f44ec6ed56a2a"}))
    app.config["BUILD_INFO_PATH"] = str(build_info_path)
    client = app.test_client()

    resp = client.get("/")

    assert resp.status_code == 200
    assert b"built 2026-08-09T00:00:00 / b38bd8e5" in resp.data
    assert b"b38bd8e5d52aee04d6452fedb09f44ec6ed56a2a" not in resp.data
