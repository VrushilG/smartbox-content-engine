FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer caching)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/app ./app

# Copy frontend static files
COPY frontend/src ./frontend/src

# Copy sample data (read-only reference, not committed secrets)
COPY data ./data

# Non-root user for security
# Pre-create writable dirs and transfer ownership before switching user
RUN adduser --disabled-password --gecos "" appuser && \
    mkdir -p /app/app/static/images /app/app/static/videos && \
    chown -R appuser:appuser /app
USER appuser

# Expose the API port
EXPOSE 8000

# Health check (PORT is injected by Railway; defaults to 8000 locally)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run the application (Railway injects $PORT; fallback 8000 for local docker run)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
