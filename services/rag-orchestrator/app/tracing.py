import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor


def setup_tracing(app, service_name: str) -> None:
    """
    Configure OpenTelemetry tracing for the RAG orchestrator.

    - Sets the global TracerProvider with resource attributes.
    - Configures an OTLP HTTP exporter to send traces to the OTel Collector.
    - Auto-instruments FastAPI, requests, redis, and httpx.

    Call exactly once at startup, right after the FastAPI app is created.
    """

    # Allow overriding endpoint via env var; fall back to in-cluster Service.
    endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_HTTP_ENDPOINT",
        "http://otel-collector.tracing.svc.cluster.local:4318/v1/traces",
    )

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "model-serving",
        }
    )

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    exporter = OTLPSpanExporter(endpoint=endpoint)

    # provider.add_span_processor(BatchSpanProcessor(exporter))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    
    # Create HTTP server spans for FastAPI routes
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health|/ready|/metrics",
    )

    # Outbound HTTP (Qdrant, external LLM, etc.)
    RequestsInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()

    # Redis cache / session store
    try:
        RedisInstrumentor().instrument()
    except Exception:
        # Do not crash the app if redis-py is not installed.
        pass
