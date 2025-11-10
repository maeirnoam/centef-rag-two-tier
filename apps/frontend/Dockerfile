# CENTEF RAG Frontend - Dockerfile for Google Cloud Run
# Lightweight container serving static files with CORS

FROM python:3.11-slim

WORKDIR /app

# Copy frontend files
COPY . .

# Expose port (Cloud Run will set PORT env var)
EXPOSE 8080

# Run the static file server
# Update serve.py to use $PORT environment variable
CMD python serve.py
