# CENTEF RAG - Google Cloud Run Deployment Guide

Complete guide for deploying the CENTEF RAG system to Google Cloud Run.

## 📋 Prerequisites

### 1. Google Cloud Setup
- Active GCP project with billing enabled
- Required APIs enabled:
  ```powershell
  gcloud services enable run.googleapis.com
  gcloud services enable cloudbuild.googleapis.com
  gcloud services enable artifactregistry.googleapis.com
  gcloud services enable aiplatform.googleapis.com
  gcloud services enable discoveryengine.googleapis.com
  gcloud services enable storage.googleapis.com
  ```

- **Required IAM Permissions**: The Cloud Run service account needs these roles:
  ```powershell
  # Get your service account (usually PROJECT_NUMBER-compute@developer.gserviceaccount.com)
  gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)"

  # Storage access for uploads/downloads
  gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

  # Discovery Engine search access
  gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/discoveryengine.editor"

  # Vertex AI access (usually granted by default)
  gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/aiplatform.user"
  ```

### 2. Local Tools
- `gcloud` CLI installed and authenticated
  ```powershell
  gcloud auth login
  gcloud config set project YOUR_PROJECT_ID
  ```
- Docker (optional for local testing)
- PowerShell (Windows) or Bash (Linux/Mac)

### 3. Environment Configuration
- Complete `.env` file with all required variables (see `.env.example`)
- Sample users initialized (run `init_users.py` if needed)
- GCS buckets created
- Vertex AI Search datastores configured

## 🚀 Deployment Process

### Option 1: Automated Deployment (Recommended)

#### Step 1: Set Project ID
```powershell
$env:PROJECT_ID = "your-project-id"
```

#### Step 2: Deploy Backend API
```powershell
cd centef-rag-fresh
.\deploy-backend.ps1
```

This will:
1. Build Docker image using Cloud Build
2. Deploy to Cloud Run with environment variables from `.env`
3. Configure service with 2GB memory, 2 CPUs
4. Test health endpoint
5. Output the API URL

**Expected output:**
```
========================================
Deployment Complete!
========================================

API Endpoints:
  Base URL:     https://centef-rag-api-abc123-uc.a.run.app
  Health:       https://centef-rag-api-abc123-uc.a.run.app/health
  ...
```

#### Step 3: Deploy Frontend
```powershell
.\deploy-frontend.ps1
```

When prompted, enter the **Backend API URL** from Step 2.

This will:
1. Update `auth.js` with the backend URL
2. Build Docker image
3. Deploy to Cloud Run with 512MB memory
4. Test frontend accessibility
5. Output the frontend URL

**Expected output:**
```
========================================
Deployment Complete!
========================================

Application URLs:
  Frontend:     https://centef-rag-frontend-abc123-uc.a.run.app
  Login:        https://centef-rag-frontend-abc123-uc.a.run.app/login.html
  ...
```

### Option 2: Manual Deployment

#### Backend API

```powershell
# Set variables
$PROJECT_ID = "your-project-id"
$REGION = "us-central1"
$SERVICE_NAME = "centef-rag-api"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Navigate to backend
cd apps\agent_api

# Build image
gcloud builds submit --tag $IMAGE_NAME --project $PROJECT_ID

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME `
  --image $IMAGE_NAME `
  --platform managed `
  --region $REGION `
  --allow-unauthenticated `
  --port 8080 `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300 `
  --max-instances 10 `
  --set-env-vars PROJECT_ID=$PROJECT_ID,VERTEX_SEARCH_LOCATION=global,... `
  --project $PROJECT_ID
```

#### Frontend

```powershell
# Set variables
$SERVICE_NAME = "centef-rag-frontend"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$SERVICE_NAME"
$BACKEND_URL = "https://centef-rag-api-abc123-uc.a.run.app"

# Update API URL in frontend
cd apps\frontend
# Manually edit js\auth.js to set API_BASE_URL

# Build image
gcloud builds submit --tag $IMAGE_NAME --project $PROJECT_ID

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME `
  --image $IMAGE_NAME `
  --platform managed `
  --region $REGION `
  --allow-unauthenticated `
  --port 8080 `
  --memory 512Mi `
  --cpu 1 `
  --timeout 60 `
  --max-instances 5 `
  --project $PROJECT_ID
```

## 🔧 Configuration

### Environment Variables

The backend requires these environment variables (set via `.env`):

```bash
# GCP Configuration
PROJECT_ID=your-project-id
VERTEX_SEARCH_LOCATION=global
GENERATION_LOCATION=us-central1

# Model Configuration
SUMMARY_MODEL=gemini-2.5-flash
GEMINI_MODEL=gemini-2.0-flash-exp

# Datastore IDs (include _gcs_store suffix)
CHUNKS_DATASTORE_ID=centef-chunk-data-store_*_gcs_store
SUMMARIES_DATASTORE_ID=centef-summaries-datastore_*_gcs_store

# Storage Buckets
SOURCE_BUCKET=centef-rag-bucket
TARGET_BUCKET=centef-rag-chunks
CHAT_HISTORY_BUCKET=centef-rag-bucket
CHAT_HISTORY_PATH=chat_history

# Authentication
JWT_SECRET_KEY=your-secret-key-here
VALID_API_KEYS=api-key-1|api-key-2  # Use pipe delimiter, NOT commas

# Note: Do NOT set PORT - Cloud Run manages this automatically
```

### Cloud Run Service Configuration

#### Backend API
- **Memory**: 2Gi (handles Gemini API calls and processing)
- **CPU**: 2 (concurrent request handling)
- **Timeout**: 300s (long-running queries and processing)
- **Max Instances**: 10 (auto-scales based on traffic)
- **Port**: 8080 (standard Cloud Run port)

#### Frontend
- **Memory**: 512Mi (static file serving)
- **CPU**: 1 (minimal compute needed)
- **Timeout**: 60s (quick responses)
- **Max Instances**: 5 (lower traffic expected)
- **Port**: 8080 (standard Cloud Run port)

### CORS Configuration

Frontend is configured to call the backend API. The backend has CORS middleware:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production Recommendation**: Update `allow_origins` in `apps/agent_api/main.py` to only allow your frontend URL.

## 🧪 Testing Deployment

### 1. Test Backend Health
```powershell
$BACKEND_URL = "https://centef-rag-api-abc123-uc.a.run.app"
Invoke-RestMethod -Uri "$BACKEND_URL/health"
# Expected: {"status":"healthy"}
```

### 2. Test Authentication
```powershell
$body = @{
    email = "admin@centef.org"
    password = "Admin123!"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "$BACKEND_URL/auth/login" -Method Post -Body $body -ContentType "application/json"
$token = $response.access_token
```

### 3. Test Chat Endpoint
```powershell
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$body = @{
    query = "What is counter-terrorism financing?"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$BACKEND_URL/chat" -Method Post -Headers $headers -Body $body
```

### 4. Test Frontend
Open in browser:
```
https://centef-rag-frontend-abc123-uc.a.run.app/login.html
```

Login with:
- **Admin**: admin@centef.org / Admin123!
- **User**: user@centef.org / User123!

## 📊 Monitoring & Logs

### View Logs
```powershell
# Backend logs
gcloud run services logs read centef-rag-api --region us-central1 --project $PROJECT_ID

# Frontend logs
gcloud run services logs read centef-rag-frontend --region us-central1 --project $PROJECT_ID
```

### Cloud Console Monitoring
1. Go to: https://console.cloud.google.com/run
2. Select your service
3. View tabs:
   - **Metrics**: Request count, latency, errors
   - **Logs**: Real-time application logs
   - **Revisions**: Deployment history

## 🔄 Updating Deployments

### Update Backend
1. Make code changes
2. Run deployment script:
   ```powershell
   .\deploy-backend.ps1
   ```
3. Cloud Run automatically routes traffic to new revision

### Update Frontend
1. Make code changes (HTML, CSS, JS)
2. Run deployment script:
   ```powershell
   .\deploy-frontend.ps1
   ```
3. Enter the backend URL (no change needed if backend URL is same)

### Rollback
```powershell
# List revisions
gcloud run revisions list --service centef-rag-api --region us-central1

# Route 100% traffic to previous revision
gcloud run services update-traffic centef-rag-api `
  --to-revisions REVISION_NAME=100 `
  --region us-central1
```

## 💰 Cost Optimization

### Estimated Costs (us-central1)
- **Backend API**: ~$0.00002448 per request + $0.024/vCPU-hour
- **Frontend**: ~$0.00001632 per request + $0.024/vCPU-hour
- **Cloud Build**: First 120 minutes/day free, then $0.003/min
- **Container Registry**: $0.026/GB storage per month

### Cost Reduction Tips
1. **Set min-instances to 0** (default) - scales to zero when idle
2. **Use --concurrency flag** to handle more requests per instance:
   ```powershell
   --concurrency 80  # Default is 80, max is 1000
   ```
3. **Reduce memory/CPU** if sufficient:
   ```powershell
   --memory 1Gi --cpu 1  # Backend
   --memory 256Mi --cpu 0.5  # Frontend (if supported)
   ```
4. **Enable request logging** only for debugging
5. **Use committed use discounts** for predictable workloads

## 🔒 Security Best Practices

### 1. Authentication
- ✅ JWT tokens with secure secret key
- ✅ Password hashing with bcrypt
- ✅ Role-based access control (admin/user)
- ⚠️ Consider adding rate limiting for API endpoints

### 2. CORS Configuration
```python
# Production: Restrict origins
allow_origins=[
    "https://centef-rag-frontend-abc123-uc.a.run.app"
]
```

### 3. Secrets Management
Instead of environment variables, use Google Secret Manager:

```powershell
# Create secret
echo "your-jwt-secret" | gcloud secrets create jwt-secret --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding jwt-secret `
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"

# Deploy with secret
gcloud run deploy centef-rag-api `
  --set-secrets=JWT_SECRET_KEY=jwt-secret:latest
```

### 4. Network Security
- Enable Cloud Armor for DDoS protection
- Use VPC connectors for private GCP resource access
- Implement IP allowlists if needed

### 5. Audit Logging
Enable Cloud Audit Logs:
```powershell
gcloud logging write user-activity "User login" --severity=INFO
```

## 🐛 Troubleshooting

### Logger Not Defined Error
**Issue**: `NameError: name 'logger' is not defined` during document processing
```
Processing error: name 'logger' is not defined
```

**Solution**: Ensure logger is initialized before use in all modules. This was fixed in `tools/processing/process_image.py` by moving logger initialization before import-time code that uses it.

### Vertex AI Import Error
**Issue**: `ImportError: cannot import name 'GenerativeModel' from 'vertexai.generative_models'`

**Solution**: Use the preview API imports:
```python
from vertexai.preview.generative_models import GenerativeModel
```

### Storage Permission Denied
**Issue**: `Permission 'storage.objects.create' denied`

**Solution**: Grant storage.objectAdmin role:
```powershell
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### Discovery Engine Permission Denied
**Issue**: `Permission 'discoveryengine.servingConfigs.search' denied`

**Solution**: Grant discoveryengine.editor role:
```powershell
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/discoveryengine.editor"
```

### Environment Variable Syntax Error
**Issue**: `Bad syntax for dict arg` when deploying

**Solution**: Use pipe delimiter (|) for list variables, not commas:
```bash
VALID_API_KEYS=key1|key2|key3
```

### PORT Environment Variable Conflict
**Issue**: "The following reserved env names were provided: PORT"

**Solution**: Remove PORT from .env file - Cloud Run sets this automatically.

### Backend Won't Deploy
**Issue**: Environment variables not set
```
ERROR: Missing required environment variable: PROJECT_ID
```

**Solution**: Ensure `.env` file exists and is complete:
```powershell
cat .env
```

### Frontend Can't Connect to Backend
**Issue**: CORS error in browser console
```
Access to fetch at 'https://...' from origin 'https://...' has been blocked by CORS policy
```

**Solution**: Check backend CORS configuration in `main.py`

### Backend Out of Memory
**Issue**: 
```
Container exceeded memory limit
```

**Solution**: Increase memory allocation:
```powershell
gcloud run services update centef-rag-api `
  --memory 4Gi `
  --region us-central1
```

### Slow Cold Starts
**Issue**: First request after idle takes 10-30 seconds

**Solution**: Set minimum instances (costs more):
```powershell
gcloud run services update centef-rag-api `
  --min-instances 1 `
  --region us-central1
```

### Authentication Fails
**Issue**: JWT token errors

**Solution**: Verify `JWT_SECRET_KEY` is same in backend deployment:
```powershell
gcloud run services describe centef-rag-api `
  --region us-central1 `
  --format "value(spec.template.spec.containers[0].env)"
```

## 📚 Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)

## 🆘 Support

For issues specific to this deployment:
1. Check Cloud Run logs
2. Verify environment variables
3. Test locally with Docker first
4. Review security settings (IAM, CORS)

For application issues:
- See main `README.md`
- Check `QUICK_START_FRONTEND.md`
- Review `ADMIN_GUIDE.md`
