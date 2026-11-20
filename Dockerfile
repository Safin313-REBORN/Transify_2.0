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
    libegl1 \
    libgles2 \
    libgomp1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application codebase and trained models
COPY . .

# Ensure data directories exist for SQLite and cache
RUN mkdir -p data/audio_cache

# Expose HTTP port
EXPOSE 8000

# Health check to ensure service readiness
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Launch the unified server
CMD ["python", "run_server.py", "--host", "0.0.0.0", "--port", "8000"]
