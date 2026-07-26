# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""test_static.py
Tests for the shared static asset route.
"""


def test_known_static_file_is_served(client):
    resp = client.get("/static/main.css")
    assert resp.status_code == 200
    assert resp.data.startswith(b"/*")


def test_unknown_static_file_404s(client):
    resp = client.get("/static/does-not-exist.css")
    assert resp.status_code == 404


def test_static_file_requires_no_authentication(client):
    resp = client.get("/static/logo.png")
    assert resp.status_code == 200
