# CENTEF RAG Backend API - Dockerfile for Google Cloud Run
# Build optimized container for FastAPI backend

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project structure (backend needs access to shared/ and tools/)
COPY . .

# Set Python path to include parent directory
ENV PYTHONPATH=/app

# Expose port (Cloud Run will set PORT env var)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Run with gunicorn for production (more robust than uvicorn alone)
CMD exec gunicorn \
    --bind :$PORT \
    --workers 2 \
    --threads 4 \
    --timeout 300 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --worker-class uvicorn.workers.UvicornWorker \
    apps.agent_api.main:app
