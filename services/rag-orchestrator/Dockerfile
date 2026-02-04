FROM python:3.11-slim

WORKDIR /app

# ---- system deps for native extensions (annoy, grpc, etc.) ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    python3-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ---- upgrade pip tooling (IMPORTANT for dependency resolution) ----
RUN python -m pip install --upgrade pip setuptools wheel

# ---- install python deps ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- copy app code ----
COPY app ./app
COPY guardrails ./guardrails

# ---- drop privileges ----
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER 10001

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
