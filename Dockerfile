# Multi-stage Dockerfile for Transify Platform
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies for OpenCV and MediaPipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libegl1 \
    libgles2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application codebase and trained models
COPY . .

# Ensure data directories exist for SQLite and cache, and prepare seed directory for persistent volume mount
RUN mkdir -p /app/data /app/data/audio_cache /app/data_seed \
    && cp -rn /app/data/* /app/data_seed/ 2>/dev/null || true

# Environment variables for SQLite database persistence
ENV TRANSIFY_DATA_DIR=/app/data \
    TRANSIFY_DB_PATH=/app/data/transify.db

# Expose HTTP port
EXPOSE 8000

# Health check to ensure service readiness
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
  CMD sh -c 'curl -fsS "http://127.0.0.1:${PORT:-8000}/api/ready" || exit 1'

# Launch the unified server with dynamic port support
CMD ["sh", "-c", "exec python run_server.py --host 0.0.0.0 --port ${PORT:-8000}"]
