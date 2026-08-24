# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""
i18n
- Localization support: Flask-Babel setup and per-request locale resolution,
per the `web-frontend-localization` spec (sweetrpg/platform's
openspec/changes/full-localization-web-apps).
"""

from flask import request
from flask_babel import Babel

DEFAULT_LOCALE = "en"
LOCALE_COOKIE_NAME = "locale"

# Locales this app can actually render. New locales land as a new
# translations/<code>/LC_MESSAGES catalog plus an entry here.
SUPPORTED_LOCALES = [DEFAULT_LOCALE]


def _resolve_locale():
    """Resolves the request locale: cookie override, then Accept-Language, then English."""
    cookie_locale = request.cookies.get(LOCALE_COOKIE_NAME)
    if cookie_locale and cookie_locale in SUPPORTED_LOCALES:
        return cookie_locale

    return request.accept_languages.best_match(SUPPORTED_LOCALES) or DEFAULT_LOCALE


babel = Babel(locale_selector=_resolve_locale)


def init_app(app):
    babel.init_app(app)
