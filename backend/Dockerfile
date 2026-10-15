FROM python:3.12-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/

WORKDIR /app/backend
# Day 4 replaces this entrypoint with the FastAPI server (uvicorn).
ENTRYPOINT ["python", "-m", "ingest.cli"]
