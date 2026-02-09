FROM python:3.11-slim


COPY services/qdrant-ingestor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/utils ./utils
COPY services/qdrant-ingestor/app ./app
COPY services/qdrant-ingestor/data ./data

ENV PYTHONPATH=/app
CMD ["python", "-m", "app.ingest"]
