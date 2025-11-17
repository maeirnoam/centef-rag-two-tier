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
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and dependencies
COPY . .

# Set Python path to include parent directory
ENV PYTHONPATH=/app

# Expose port (Cloud Run will set PORT env var)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Add startup script that downloads YouTube cookies using Python
RUN echo '#!/bin/bash\n\
echo "=== Container Startup Debug ===" \n\
echo "Python path: $PYTHONPATH" \n\
echo "Working directory: $(pwd)" \n\
\n\
# Download YouTube cookies if configured \n\
if [ ! -z "$YOUTUBE_COOKIES_BUCKET" ]; then \n\
    echo "Downloading YouTube cookies from GCS..." \n\
    mkdir -p /tmp/yt-dlp \n\
    python -c "\n\
from google.cloud import storage\n\
import os\n\
try:\n\
    client = storage.Client()\n\
    bucket = client.bucket(os.environ[\"YOUTUBE_COOKIES_BUCKET\"])\n\
    blob = bucket.blob(\"yt-dlp-cookies/youtube_cookies.txt\")\n\
    blob.download_to_filename(\"/tmp/yt-dlp/youtube_cookies.txt\")\n\
    print(\"✓ YouTube cookies downloaded successfully\")\n\
except Exception as e:\n\
    print(f\"⚠ Cookies download failed: {e}\")\n\
    exit(1)\n\
" \n\
    if [ $? -eq 0 ]; then \n\
        ls -la /tmp/yt-dlp/youtube_cookies.txt \n\
        echo "✓ YouTube cookies configured at: /tmp/yt-dlp/youtube_cookies.txt" \n\
    else \n\
        echo "⚠ Continuing without YouTube authentication" \n\
    fi \n\
else \n\
    echo "⚠ YOUTUBE_COOKIES_BUCKET not set - YouTube downloads may fail" \n\
fi \n\
\n\
echo "Directory contents:" \n\
ls -la \n\
echo "Apps directory:" \n\
ls -la apps/ 2>/dev/null || echo "No apps directory" \n\
echo "Shared directory:" \n\
ls -la shared/ 2>/dev/null || echo "No shared directory" \n\
echo "Testing Python imports..." \n\
python -c "import sys; print(\"sys.path:\", sys.path)" \n\
python -c "from apps.agent_api import main; print(\"Import successful!\")" || echo "Import failed!" \n\
echo "=== Starting gunicorn ===" \n\
exec gunicorn \\\n\
    --bind :$PORT \\\n\
    --workers 2 \\\n\
    --threads 4 \\\n\
    --timeout 300 \\\n\
    --access-logfile - \\\n\
    --error-logfile - \\\n\
    --log-level debug \\\n\
    --worker-class uvicorn.workers.UvicornWorker \\\n\
    apps.agent_api.main:app \n\
' > /app/start.sh && chmod +x /app/start.sh

# Run with debug startup script
CMD ["/app/start.sh"]
