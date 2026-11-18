# ── Stage 1: build deps ───────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="Team SingleThread — SEVA FIRST 2026"
LABEL org.opencontainers.image.title="SurakshaEdge"
LABEL org.opencontainers.image.description="Edge AI assault detection — REG-008-OP-024"
LABEL org.opencontainers.image.version="0.1.0"

# Non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=appuser:appuser . .

# Create writable results dir
RUN mkdir -p results && chown appuser:appuser results

USER appuser

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SURAKSHA_PRODUCTION=false \
    SURAKSHA_API_TOKEN=change-me-in-production \
    SURAKSHA_CONFIG=configs/demo.yaml \
    PORT=8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
