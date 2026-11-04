# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""test_footer.py
Tests for the standard three-line site footer on the main page.
"""

import datetime
import re

import pytest


def _lines(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    return html, re.findall(r'<span class="(footer-line[^"]*)">(.*?)</span>', html, re.S)


def test_footer_has_three_lines_in_order(client):
    _, lines = _lines(client)

    assert len(lines) == 3
    assert f"&copy; {datetime.datetime.now(datetime.timezone.utc).year} Pilgrimage Software" in lines[0][1]
    assert [t for t in ("Terms of Service", "Privacy Policy", "Support") if t in lines[1][1]] == [
        "Terms of Service",
        "Privacy Policy",
        "Support",
    ]
    assert re.search(r"v\S+ &middot; built \S+ / \S+", lines[2][1])


def test_last_line_is_build_line(client):
    _, lines = _lines(client)

    assert lines[2][0] == "footer-line footer-build"


@pytest.mark.parametrize(
    "root_url,expected",
    [("/", "/terms"), ("https://dev.sweetrpg.com/", "https://dev.sweetrpg.com/terms")],
)
def test_terms_link_is_site_root(app, client, root_url, expected):
    app.config["ROOT_URL"] = root_url

    html, _ = _lines(client)

    assert f'<a href="{expected}">Terms of Service</a>' in html


def test_terms_link_is_not_prefixed_under_app_base_path(app, client):
    app.config["ROOT_URL"] = "/"
    app.config["APPLICATION_BASE_PATH"] = "/assets"

    html, _ = _lines(client)

    assert 'href="/terms"' in html
    assert "/assets/terms" not in html
