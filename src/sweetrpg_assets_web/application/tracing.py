# -*- coding: utf-8 -*-
__author__ = "Paul Schifferer <dm@sweetrpg.com>"
"""tracing.py
Bootstraps distributed tracing, exported via OTLP/HTTP to the cluster's collector (Tempo) - see
`OTEL_EXPORTER_OTLP_ENDPOINT` in the deployment configmap.

The tracer provider is created once and lives for the process's lifetime - it is never
shut down from within a setup helper. catalog-api shipped exactly that bug (a `defer
TeardownTracing()` scoped to a setup function instead of `main()`), which shut its tracer down
within milliseconds of startup and silently dropped every span with no visible error. Don't
repeat it here: if a teardown hook is ever added, it belongs on the WSGI server's actual
shutdown, not this function's return.
"""

from flask import Flask
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from sweetrpg_assets_web.application import constants


def setup_tracing(app: Flask, service_name: str = constants.APPLICATION_NAME) -> None:
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    # Endpoint comes from OTEL_EXPORTER_OTLP_ENDPOINT via the SDK's own env var handling if
    # unset here; passed explicitly only when the app config overrides it.
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    FlaskInstrumentor().instrument_app(app)
