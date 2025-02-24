"""OpenTelemetry tracing configuration."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.semconv.resource import ResourceAttributes

from orchestrator.config import ObservabilitySettings


def setup_tracing(settings: ObservabilitySettings) -> None:
    """Configure OpenTelemetry tracing."""
    if not settings.tracing_enabled:
        return

    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: settings.service_name,
        ResourceAttributes.SERVICE_VERSION: "1.0.0",
    })

    provider = TracerProvider(resource=resource)

    # Console exporter for development
    console_exporter = ConsoleSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(console_exporter))

    # OTLP exporter for production
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        otlp_exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    except ImportError:
        pass

    trace.set_tracer_provider(provider)


def get_tracer(name: str = "orchestrator") -> trace.Tracer:
    """Get a tracer instance."""
    return trace.get_tracer(name)
