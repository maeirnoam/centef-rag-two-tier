# Successful Cloud Run Deployment Summary

## Overview
Successfully deployed CENTEF RAG system to Google Cloud Run with full functionality including:
- Document upload and processing (PDF, DOCX, Images, SRT)
- Chunk extraction and summarization with Gemini
- Two-tier search with Vertex AI Discovery Engine
- User authentication and chat history
- Admin approval workflow for documents

## Project Configuration

**Project Details:**
- Project ID: `sylvan-faculty-476113-c9`
- Region: `us-central1`
- Service Account: `51695993895-compute@developer.gserviceaccount.com`

**Deployed Services:**
- Backend API: `https://centef-rag-api-51695993895.us-central1.run.app`
- Frontend: `https://centef-rag-frontend-51695993895.us-central1.run.app`

**Container Registry:**
- Artifact Registry: `us-central1-docker.pkg.dev/sylvan-faculty-476113-c9/centef-rag`

## Issues Fixed and Solutions

### 1. Logger Not Defined Error
**Problem:** `NameError: name 'logger' is not defined` when uploading documents
**Root Cause:** In `tools/processing/process_image.py`, logger was used at module import time (line 20) before being defined (line 39)
**Solution:** Moved logger initialization to before the Vision API import attempt
**File:** [tools/processing/process_image.py](tools/processing/process_image.py)
```python
# Setup logging first (before imports that use it)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Now imports can safely use logger
try:
    from google.cloud import vision
    VISION_API_AVAILABLE = True
except ImportError:
    VISION_API_AVAILABLE = False
    logger.warning("Google Cloud Vision API not available, will use Tesseract")
```

### 2. Vertex AI Import Error
**Problem:** `ImportError: cannot import name 'GenerativeModel' from 'vertexai.generative_models'`
**Root Cause:** Using deprecated import path instead of preview API
**Solution:** Updated imports in multiple files to use `vertexai.preview.generative_models`
**Files Fixed:**
- [apps/agent_api/synthesizer.py](apps/agent_api/synthesizer.py)
- [tools/processing/summarize_chunks.py](tools/processing/summarize_chunks.py)

```python
# Changed from:
from vertexai.generative_models import GenerativeModel

# To:
from vertexai.preview.generative_models import GenerativeModel
```

### 3. Environment Variable Conflicts
**Problem:** "The following reserved env names were provided: PORT"
**Solution:** Removed PORT from .env file as Cloud Run sets this automatically
**File:** [.env](.env)

### 4. Storage Permissions Error
**Problem:** `Permission 'storage.objects.create' denied` during login/upload
**Solution:** Granted storage.objectAdmin role to service account
```bash
gcloud projects add-iam-policy-binding sylvan-faculty-476113-c9 \
  --member="serviceAccount:51695993895-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### 5. Discovery Engine Permissions Error
**Problem:** `Permission 'discoveryengine.servingConfigs.search' denied` during chat
**Solution:** Granted discoveryengine.editor role to service account
```bash
gcloud projects add-iam-policy-binding sylvan-faculty-476113-c9 \
  --member="serviceAccount:51695993895-compute@developer.gserviceaccount.com" \
  --role="roles/discoveryengine.editor"
```

## Required IAM Permissions

The Cloud Run service account needs the following roles:

```bash
# Storage access for document uploads and retrieval
gcloud projects add-iam-policy-binding sylvan-faculty-476113-c9 \
  --member="serviceAccount:51695993895-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Discovery Engine access for search functionality
gcloud projects add-iam-policy-binding sylvan-faculty-476113-c9 \
  --member="serviceAccount:51695993895-compute@developer.gserviceaccount.com" \
  --role="roles/discoveryengine.editor"

# Vertex AI access for Gemini summarization (usually granted by default)
gcloud projects add-iam-policy-binding sylvan-faculty-476113-c9 \
  --member="serviceAccount:51695993895-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

## Deployment Scripts

### Backend Deployment
**Script:** [deploy-backend-simple.ps1](deploy-backend-simple.ps1)
- Builds Docker image using Cloud Build with cloudbuild.yaml
- Deploys to Cloud Run with environment variables from .env
- Uses Artifact Registry for container images

**Command:**
```powershell
.\deploy-backend-simple.ps1
```

### Frontend Deployment
**Script:** [deploy-frontend-simple.ps1](deploy-frontend-simple.ps1)
- Builds and deploys frontend container
- Configures CORS for backend communication

**Command:**
```powershell
.\deploy-frontend-simple.ps1
```

## Environment Variables

All configuration is managed through `.env` file (not committed to repo):

```bash
# Google Cloud Configuration
PROJECT_ID=sylvan-faculty-476113-c9
REGION=us-central1

# Storage Buckets
SOURCE_BUCKET=centef-rag-bucket
TARGET_BUCKET=centef-rag-chunks
CHAT_HISTORY_BUCKET=centef-rag-bucket

# Vertex AI Discovery Engine Datastores
CHUNKS_DATASTORE_ID=centef-chunk-data-store_1761831236752_gcs_store
SUMMARIES_DATASTORE_ID=centef-summaries-datastore_1762162632284_gcs_store

# API Authentication
VALID_API_KEYS=key1|key2|key3  # Use pipe delimiter, not commas
JWT_SECRET_KEY=your-secret-key-change-in-production

# AI Models
GEMINI_MODEL=gemini-2.0-flash-exp

# Note: PORT is NOT set here - Cloud Run manages this automatically
```

## Successful Deployment Process

1. **Prepare environment:**
   - Set up .env file with all required variables
   - Ensure Artifact Registry repository exists

2. **Deploy backend:**
   ```powershell
   .\deploy-backend-simple.ps1
   ```

3. **Deploy frontend:**
   ```powershell
   .\deploy-frontend-simple.ps1
   ```

4. **Grant permissions:**
   ```bash
   # Storage permissions
   gcloud projects add-iam-policy-binding sylvan-faculty-476113-c9 \
     --member="serviceAccount:51695993895-compute@developer.gserviceaccount.com" \
     --role="roles/storage.objectAdmin"

   # Discovery Engine permissions
   gcloud projects add-iam-policy-binding sylvan-faculty-476113-c9 \
     --member="serviceAccount:51695993895-compute@developer.gserviceaccount.com" \
     --role="roles/discoveryengine.editor"
   ```

5. **Verify deployment:**
   - Test login at frontend URL
   - Upload a test document
   - Verify document processing (chunks + summary)
   - Test chat functionality with search

## Monitoring and Logs

### View Cloud Run Logs
```bash
# Recent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=centef-rag-api AND resource.labels.location=us-central1" \
  --limit 50 \
  --project sylvan-faculty-476113-c9

# Stream logs in real-time
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=centef-rag-api" \
  --project sylvan-faculty-476113-c9
```

### Check Service Health
```bash
# Backend health
curl https://centef-rag-api-51695993895.us-central1.run.app/health

# View service details
gcloud run services describe centef-rag-api --region us-central1 --project sylvan-faculty-476113-c9
```

## Working Features

✅ **User Authentication**
- JWT-based login system
- Role-based access control (admin/teacher/student)
- User management with GCS backend

✅ **Document Upload & Processing**
- PDF processing with PyMuPDF
- DOCX processing with python-docx
- Image OCR with Tesseract (fallback from Vision API)
- SRT subtitle processing
- Background processing with FastAPI BackgroundTasks

✅ **AI-Powered Summarization**
- Chunk extraction from documents
- Gemini-based summarization
- Metadata extraction (title, author, topics)
- JSON-structured output

✅ **Two-Tier Search**
- Vertex AI Discovery Engine integration
- Chunk-level detailed search
- Summary-level broad search
- Relevance scoring and deduplication

✅ **Chat Interface**
- Session-based conversations
- Message history persistence
- Source citations with page references
- Multi-turn context awareness

✅ **Admin Workflow**
- Document approval system
- Manifest management
- Source deletion with cleanup
- Status tracking

## Key Takeaways

1. **Logger initialization order matters** - Define loggers before using them in module-level code
2. **Use Vertex AI preview APIs** - The stable API paths may be outdated
3. **Environment variable delimiters** - Use pipes (|) not commas for lists in gcloud
4. **Cloud Run manages PORT** - Don't set PORT in environment variables
5. **IAM permissions are critical** - Grant storage and Discovery Engine access to service account
6. **Artifact Registry over Container Registry** - Use newer Artifact Registry for better control

## Next Steps

- Monitor logs for any errors during production use
- Set up alerts for service failures
- Consider implementing rate limiting
- Add monitoring dashboards in Cloud Console
- Set up backup/disaster recovery procedures
- Review and rotate JWT secret keys regularly
