FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY /app/ingest.py /app/ingest.py
COPY /app/utils.py /app/utils.py

ENTRYPOINT ["python", "/app/ingest.py"]
