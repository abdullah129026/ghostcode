# GhostCode API: FastAPI + the tree-sitter analysis pipeline.
# Build context is the repo root (render.yaml points here).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/ghostcode/backend

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .

# run as non-root; analysis tempdirs live under /tmp either way
RUN useradd -m -u 10001 ghostcode && chown -R ghostcode:ghostcode /srv/ghostcode
USER ghostcode

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

# single worker: the rate limiter is per-process by design (see api/security.py)
CMD ["sh", "-c", "uvicorn api.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
