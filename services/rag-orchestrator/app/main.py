import os
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from opentelemetry import trace
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

from schemas import ChatRequest, ChatResponse
from retriever import Retriever
from llm_client import KServeLLMClient
from session import SessionStore
from logging import api_logger
from metrics import (
    CHAT_REQUEST_COUNT,
    CHAT_LATENCY,
)

# OpenTelemetry setup
def setup_tracing(app: FastAPI):
    service_name = os.getenv("OTEL_SERVICE_NAME", "rag-orchestrator")
    otlp_endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "http://otel-collector.tracing.svc.cluster.local:4317",
    )

    resource = Resource.create({"service.name": service_name})

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True,
    )

    provider.add_span_processor(BatchSpanProcessor(exporter))

    # Auto-instrument inbound + outbound
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/metrics|/health|/ready",
    )
    RequestsInstrumentor().instrument()
    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()



# App init
app = FastAPI(title="RAG Orchestrator")

setup_tracing(app)
tracer = trace.get_tracer("rag-orchestrator")

retriever = Retriever() if os.getenv("ENABLE_RETRIEVER", "true") == "true" else None
kserve = KServeLLMClient()
sessions = SessionStore()



# Middleware: logging + trace correlation
@app.middleware("http")
async def api_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Attach trace info to request.state for log correlation
    span = otel_trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.is_valid:
        request.state.trace_id = format(ctx.trace_id, "032x")
        request.state.span_id = format(ctx.span_id, "016x")
    else:
        request.state.trace_id = None
        request.state.span_id = None

    start = time.time()
    response = await call_next(request)
    latency_ms = round((time.time() - start) * 1000.0, 2)

    api_logger.info(
        request=request,
        response=response,
        latency_ms=latency_ms,
    )

    return response



# Health
@app.get("/health")
def health():
    return {"status": "ok"}



# Chat endpoint (FULLY TRACED)
@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    start_time = time.time()

    with tracer.start_as_current_span("rag.chat") as root_span:
        root_span.set_attribute("session.id", req.session_id or "new")
        root_span.set_attribute("rag.top_k", int(os.getenv("RAG_TOP_K", "4")))

        
        # Load session (Redis auto-instrumented)
        history = sessions.get(req.session_id)

        
        # Retrieval (Qdrant)
        with tracer.start_as_current_span("retrieval.vector_search") as span:
            span.set_attribute("vector.db", "qdrant")
            span.set_attribute(
                "vector.collection",
                os.getenv("QDRANT_COLLECTION", "medical_docs"),
            )
            span.set_attribute("vector.top_k", int(os.getenv("RAG_TOP_K", "4")))

            t0 = time.time()
            chunks = retriever.retrieve(req.message) if retriever else []
            retrieval_ms = round((time.time() - t0) * 1000.0, 2)

            span.set_attribute("retrieval.chunks", len(chunks))

        request.state.retrieval_ms = retrieval_ms
        request.state.chunks_returned = len(chunks)

        
        # Prompt construction
        prompt = kserve.build_prompt(
            question=req.message,
            context_chunks=chunks,
            history=history,
        )

        
        # LLM inference
        
        with tracer.start_as_current_span("llm.inference") as span:
            span.set_attribute("llm.provider", "kserve")
            span.set_attribute(
                "llm.model",
                os.getenv("LLM_MODEL_ID", "unknown"),
            )
            span.set_attribute(
                "llm.max_tokens",
                int(os.getenv("LLM_MAX_TOKENS", "512")),
            )
            span.set_attribute(
                "llm.temperature",
                float(os.getenv("LLM_TEMPERATURE", "0.2")),
            )

            answer = kserve.generate(
                prompt,
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "512")),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
            )

        
        # Persist session
        
        sessions.append(req.session_id, req.message, answer)

        
        # Metrics
        
        latency_ms = round((time.time() - start_time) * 1000.0, 2)
        CHAT_REQUEST_COUNT.inc()
        CHAT_LATENCY.observe(latency_ms)

        return ChatResponse(
            answer=answer,
            latency_ms=latency_ms,
            chunks_used=len(chunks),
            session_id=req.session_id,
        )
