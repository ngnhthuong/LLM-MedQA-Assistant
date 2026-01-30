from uuid import uuid4
import time
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# -----------------------
# Internal modules
# -----------------------
from .session import SessionStore
from .health import readiness
from .logging import log_request
from .retriever import build_retriever_from_env
from .prompt import build_prompt
from .llm_client import build_kserve_client_from_env
from .schemas import ChatRequest, ChatResponse
from .metrics import (
    RAG_CHAT_REQUESTS_TOTAL,
    RAG_CHAT_ERRORS_TOTAL,
    RAG_RETRIEVAL_LATENCY_SECONDS,
    RAG_CONTEXT_TOKENS,
    RAG_EMPTY_CONTEXT_TOTAL,
    RAG_GENERATION_LATENCY_SECONDS,
    RAG_FALLBACK_TOTAL,
    RAG_INFLIGHT,
)

# -----------------------
# Tracing (single source)
# -----------------------
from opentelemetry import trace
from .tracing import setup_tracing

# -----------------------
# App bootstrap
# -----------------------
app = FastAPI(title="Medical RAG Orchestrator")

setup_tracing(
    app=app,
    service_name="rag-orchestrator",
)

tracer = trace.get_tracer("rag-orchestrator")

# -----------------------
# Session store
# -----------------------
session_store = SessionStore()

# -----------------------
# Global exception handler
# -----------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    RAG_CHAT_ERRORS_TOTAL.inc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

# -----------------------
# Health
# -----------------------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    return readiness()

# -----------------------
# Prometheus metrics
# -----------------------
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# -----------------------
# API logging middleware
# -----------------------
@app.middleware("http")
async def api_logging_middleware(request: Request, call_next):
    if request.url.path.startswith("/api"):
        start = time.time()
        request_id = str(uuid4())
        request.state.request_id = request_id

        # trace ↔ log correlation
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.is_valid:
            request.state.trace_id = format(ctx.trace_id, "032x")
            request.state.span_id = format(ctx.span_id, "016x")
        else:
            request.state.trace_id = None
            request.state.span_id = None

        response = None
        try:
            response = await call_next(request)
            status_code = getattr(response, "status_code", 500)
        except Exception as exc:
            request.state.error_message = str(exc)
            status_code = 500
            raise
        finally:
            await log_request(request, status_code, start)

        return response

    return await call_next(request)

# -----------------------
# Chat endpoint
# -----------------------
@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    RAG_CHAT_REQUESTS_TOTAL.inc()
    RAG_INFLIGHT.inc()

    try:
        with tracer.start_as_current_span("rag.chat") as root_span:
            session_id = req.session_id or str(uuid4())
            request.state.session_id = session_id
            root_span.set_attribute("session.id", session_id)

            # -----------------------
            # Persist user message
            # -----------------------
            session_store.append(session_id, "user", req.message)
            history = session_store.get_history(session_id)

            # -----------------------
            # Retrieval
            # -----------------------
            retriever = build_retriever_from_env()

            with tracer.start_as_current_span("retrieval.vector_search") as span:
                span.set_attribute("vector.db", "qdrant")
                span.set_attribute(
                    "vector.collection",
                    os.getenv("QDRANT_COLLECTION", "medical_docs"),
                )
                span.set_attribute(
                    "vector.top_k",
                    int(os.getenv("RAG_TOP_K", "4")),
                )

                t0 = time.time()
                chunks = retriever.retrieve(req.message) if retriever else []
                retrieval_ms = round((time.time() - t0) * 1000.0, 2)

                span.set_attribute("retrieval.chunks", len(chunks))

            RAG_RETRIEVAL_LATENCY_SECONDS.observe(retrieval_ms / 1000.0)
            request.state.retrieval_ms = retrieval_ms
            request.state.chunks_returned = len(chunks)

            # -----------------------
            # Context metrics
            # -----------------------
            est_tokens = sum(max(1, len(c.text) // 4) for c in chunks)
            RAG_CONTEXT_TOKENS.observe(est_tokens)

            if not chunks:
                RAG_EMPTY_CONTEXT_TOTAL.inc()

            # -----------------------
            # Prompt
            # -----------------------
            prompt = build_prompt(
                req.message,
                chunks,
                chat_history=history,
            )

            # -----------------------
            # LLM inference
            # -----------------------
            kserve = build_kserve_client_from_env()

            with tracer.start_as_current_span("llm.inference") as span:
                span.set_attribute("llm.provider", "kserve")
                span.set_attribute(
                    "llm.model",
                    os.getenv("LLM_MODEL_ID", "unknown"),
                )

                g0 = time.time()
                if kserve:
                    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "512"))
                    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
                    answer = kserve.generate(
                        prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                else:
                    RAG_FALLBACK_TOTAL.inc()
                    if chunks:
                        answer = (
                            "General information based on available context:\n\n"
                            + "\n\n".join(
                                f"- {c.text} [source:{c.id}]"
                                for c in chunks[:3]
                            )
                            + "\n\n(Configure KSERVE_URL for full generation.)"
                        )
                    else:
                        answer = (
                            "I don't have enough context. "
                            "Ingest documents into Qdrant first."
                        )

                llm_ms = round((time.time() - g0) * 1000.0, 2)

            RAG_GENERATION_LATENCY_SECONDS.observe(llm_ms / 1000.0)
            request.state.llm_ms = llm_ms

            # -----------------------
            # Persist assistant reply
            # -----------------------
            session_store.append(session_id, "assistant", answer)
            history = session_store.get_history(session_id)

            return ChatResponse(
                session_id=session_id,
                answer=answer,
                history=history,
                context_used=len(chunks),
            )

    finally:
        RAG_INFLIGHT.dec()
