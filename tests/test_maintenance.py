# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""
Tests for the maintenance-mode redirect behavior.
"""

from urllib.parse import parse_qs, urlparse

from sweetrpg_admin_api_client import MaintenanceMode


def test_active_mode_redirects_to_shared_maintenance_page(app, client):
    app.admin_client.fetch_maintenance_modes = lambda scopes: [
        MaintenanceMode(
            scope_type="service",
            scope_value="assets",
            label="Scheduled maintenance",
            description="Upgrading infrastructure",
            starts_at="2026-08-01T00:00:00Z",
            ends_at="2026-08-01T02:00:00Z",
        )
    ]

    response = client.get("/")

    # Maintenance is a deliberate state: redirect to the shared page, not a 503.
    assert response.status_code == 302
    url = urlparse(response.headers["Location"])
    assert url.path.endswith("/maintenance")
    query = parse_qs(url.query)
    assert query["service"] == ["assets-web"]
    assert query["label"] == ["Scheduled maintenance"]


def test_redirect_omits_empty_record_fields(app, client):
    app.admin_client.fetch_maintenance_modes = lambda scopes: [
        MaintenanceMode(
            scope_type="platform",
            scope_value="",
            label=None,
            description=None,
            starts_at=None,
            ends_at=None,
        )
    ]

    response = client.get("/")

    assert response.status_code == 302
    query = parse_qs(urlparse(response.headers["Location"]).query)
    assert set(query) == {"service"}


def test_normal_request_proceeds_when_no_maintenance_mode_active(app, client):
    app.admin_client.fetch_maintenance_modes = lambda scopes: []

    response = client.get("/")

    assert response.status_code != 503
    assert response.status_code != 302


def test_fail_open_when_admin_api_unreachable(app, client):
    """The fail-open contract is unchanged: an unreachable admin-api means normal rendering."""

    def boom(scopes):
        raise ConnectionError("admin-api unreachable")

    app.admin_client.fetch_maintenance_modes = boom

    response = client.get("/")

    assert response.status_code != 503
    assert response.status_code != 302


def test_fail_open_when_admin_client_missing(app, client):
    saved_client = app.admin_client
    del app.admin_client
    try:
        response = client.get("/")
        assert response.status_code != 503
        assert response.status_code != 302
    finally:
        app.admin_client = saved_client
