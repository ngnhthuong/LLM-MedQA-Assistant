FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY guardrails_app.py ./guardrails_app.py
COPY guardrails ./guardrails

# run non-root containers.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER 10001

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
