"""OpenTelemetry setup for SecureClaim AI (task 1.1.6)."""
from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.config import cfg


def init_telemetry(app) -> None:
    resource = Resource({"service.name": cfg.otel_service_name})
    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(endpoint=cfg.otel_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
