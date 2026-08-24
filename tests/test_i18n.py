# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""test_i18n.py
Tests for per-request locale resolution (cookie override -> Accept-Language -> English).
"""

import pytest
from flask import Flask

from sweetrpg_assets_web.application.i18n import LOCALE_COOKIE_NAME, _resolve_locale, babel


@pytest.fixture
def locale_app():
    app = Flask("test")
    babel.init_app(app)
    return app


def resolve(app, headers=None, cookies=None):
    with app.test_request_context(headers=headers, environ_base=None) as ctx:
        if cookies:
            for name, value in cookies.items():
                ctx.request.cookies = type(ctx.request.cookies)(
                    {**ctx.request.cookies, name: value}
                )
        return _resolve_locale()


def test_cookie_override_wins(locale_app):
    assert (
        resolve(
            locale_app,
            headers={"Accept-Language": "fr"},
            cookies={LOCALE_COOKIE_NAME: "en"},
        )
        == "en"
    )


def test_unsupported_cookie_falls_through_to_accept_language(locale_app):
    assert (
        resolve(
            locale_app,
            headers={"Accept-Language": "en-GB,en;q=0.9"},
            cookies={LOCALE_COOKIE_NAME: "zz"},
        )
        == "en"
    )


def test_accept_language_region_tag_matches_base_locale(locale_app):
    assert resolve(locale_app, headers={"Accept-Language": "en-GB,en;q=0.9"}) == "en"


def test_unsupported_accept_language_falls_back_to_english(locale_app):
    # best_match() returns None for a header with no supported tag - fall back to en.
    assert resolve(locale_app, headers={"Accept-Language": "fr-CA,fr;q=0.9"}) == "en"


def test_missing_everything_falls_back_to_english(locale_app):
    assert resolve(locale_app) == "en"
