from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
import os

def setup_tracing():
    service_name = os.getenv("OTEL_SERVICE_NAME", "streamlit-ui")

    provider = TracerProvider(
        resource=Resource.create({"service.name": service_name})
    )

    exporter = OTLPSpanExporter(
        endpoint=os.getenv(
            "OTEL_EXPORTER_OTLP_HTTP_ENDPOINT",
            "http://otel-collector.tracing.svc.cluster.local:4318/v1/traces"
        )
    )

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Instrument outgoing HTTP calls
    RequestsInstrumentor().instrument()
