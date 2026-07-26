# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""metrics.py
Prometheus metrics at `/metrics`, scraped via a PodMonitor - the Flask equivalent of the Go
services' `gin-metrics` convention (docs/service-conventions.md's Telemetry section).
"""

from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics


def setup_metrics(app: Flask) -> PrometheusMetrics:
    return PrometheusMetrics(app, path="/metrics")
