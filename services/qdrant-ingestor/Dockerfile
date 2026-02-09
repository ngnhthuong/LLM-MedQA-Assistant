FROM python:3.11-slim

WORKDIR /app

COPY services/qdrant-ingestor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/qdrant-ingestor/app ./app
COPY services/utils ./utils

ENV PYTHONPATH=/app

CMD ["python", "-m", "app.ingest"]
