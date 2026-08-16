# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""test_maintenance.py
Tests for the maintenance-mode check in the `web` blueprint's before_request hook.
"""

from sweetrpg_admin_api_client import MaintenanceMode


def _mode(**overrides):
    fields = dict(
        scope_type="platform",
        scope_value="",
        label="Scheduled Maintenance",
        description="We are upgrading the platform.",
        starts_at="2026-08-01T00:00:00Z",
        ends_at="2026-08-01T02:00:00Z",
    )
    fields.update(overrides)
    return MaintenanceMode(**fields)


def test_normal_page_renders_when_no_maintenance_mode_is_active(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Assets Service" in resp.data


def test_maintenance_page_renders_when_a_mode_is_active(app, client):
    app.admin_client.fetch_maintenance_modes = lambda scopes: [_mode()]

    resp = client.get("/")

    assert resp.status_code == 503
    assert b"Scheduled Maintenance" in resp.data
    assert b"We are upgrading the platform." in resp.data
    assert b"2026-08-01T00:00:00Z" in resp.data
    assert b"2026-08-01T02:00:00Z" in resp.data


def test_maintenance_mode_also_gates_other_routes(app, client):
    app.admin_client.fetch_maintenance_modes = lambda scopes: [_mode()]

    resp = client.get("/asset/avatar/does-not-exist")

    assert resp.status_code == 503
    assert b"Scheduled Maintenance" in resp.data


def test_admin_api_unreachable_falls_back_to_normal_rendering(app, client):
    def _raise(scopes):
        raise RuntimeError("simulated admin-api failure")

    app.admin_client.fetch_maintenance_modes = _raise

    resp = client.get("/")

    assert resp.status_code == 200
    assert b"Assets Service" in resp.data


def test_health_endpoint_stays_reachable_during_maintenance(app, client):
    app.admin_client.fetch_maintenance_modes = lambda scopes: [_mode()]

    resp = client.get("/health/ping")

    assert resp.status_code == 200
    assert resp.data == b"pong"
