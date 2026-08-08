# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""test_static.py
Tests for the shared static asset route.
"""


def test_known_static_file_is_served(client):
    resp = client.get("/static/css/main.css")
    assert resp.status_code == 200
    assert resp.data.startswith(b"/*")


def test_unknown_static_file_404s(client):
    resp = client.get("/static/does-not-exist.css")
    assert resp.status_code == 404


def test_static_file_requires_no_authentication(client):
    resp = client.get("/static/img/logo.png")
    assert resp.status_code == 200


def test_avatar_menu_css_is_served(client):
    resp = client.get("/static/css/avatar-menu.css")
    assert resp.status_code == 200
    assert resp.data.startswith(b"/*")


def test_avatar_menu_js_is_served(client):
    resp = client.get("/static/js/avatar-menu.js")
    assert resp.status_code == 200
    assert b"avatar-menu" in resp.data


def test_theme_js_is_served(client):
    resp = client.get("/static/js/theme.js")
    assert resp.status_code == 200
    assert b"avatar-menu-theme-row" in resp.data


def test_mystery_man_svg_is_served(client):
    resp = client.get("/static/img/mystery-man.svg")
    assert resp.status_code == 200
    assert resp.data.startswith(b"<svg")
