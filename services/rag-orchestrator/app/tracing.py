from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

def setup_tracing(service_name: str):
    resource = Resource.create({
        "service.name": service_name,
        "service.namespace": "model-serving",
    })

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    exporter = OTLPSpanExporter(
        endpoint="http://otel-collector.tracing.svc.cluster.local:4318/v1/traces"
    )

    provider.add_span_processor(
        BatchSpanProcessor(exporter)
    )
