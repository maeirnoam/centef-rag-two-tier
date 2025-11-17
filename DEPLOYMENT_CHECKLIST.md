# Google Cloud Run Deployment - Pre-Flight Checklist

## ☑️ Before You Start

### 1. Google Cloud Project Setup
- [ ] GCP project created
- [ ] Billing account linked and active
- [ ] Project ID noted: `_______________________`

### 2. Required APIs Enabled
Run these commands to enable all required APIs:
```powershell
$PROJECT_ID = "your-project-id"

gcloud services enable run.googleapis.com --project $PROJECT_ID
gcloud services enable cloudbuild.googleapis.com --project $PROJECT_ID
gcloud services enable containerregistry.googleapis.com --project $PROJECT_ID
gcloud services enable aiplatform.googleapis.com --project $PROJECT_ID
gcloud services enable discoveryengine.googleapis.com --project $PROJECT_ID
gcloud services enable storage.googleapis.com --project $PROJECT_ID
```

Check status:
- [ ] Cloud Run API
- [ ] Cloud Build API
- [ ] Container Registry API
- [ ] Vertex AI API
- [ ] Discovery Engine API
- [ ] Cloud Storage API

### 3. Local Tools Installed
- [ ] `gcloud` CLI installed ([Download](https://cloud.google.com/sdk/docs/install))
- [ ] PowerShell 5.1+ (Windows) or Bash (Linux/Mac)
- [ ] Docker (optional, for local testing)
- [ ] Python 3.10+ (for local development)

### 4. Authentication Configured
```powershell
# Login to Google Cloud
gcloud auth login

# Set default project
gcloud config set project YOUR_PROJECT_ID

# Verify authentication
gcloud auth list
```

- [ ] Authenticated with Google Cloud
- [ ] Default project set
- [ ] Application default credentials configured

### 5. GCP Resources Created
- [ ] Source bucket exists: `gs://centef-rag-bucket`
- [ ] Target bucket exists: `gs://centef-rag-chunks`
- [ ] Chat history path configured in source bucket
- [ ] Vertex AI Search app created
- [ ] Chunks datastore created with `_gcs_store` suffix
- [ ] Summaries datastore created with `_gcs_store` suffix

### 6. Environment Configuration
- [ ] `.env` file exists in `centef-rag-fresh/` directory
- [ ] All required variables set (see checklist below)
- [ ] JWT_SECRET_KEY is strong (32+ characters)
- [ ] Datastore IDs include `_gcs_store` suffix

#### Required Environment Variables
```bash
# GCP Configuration
PROJECT_ID=                        # Your GCP project ID
VERTEX_SEARCH_LOCATION=            # e.g., global
GENERATION_LOCATION=               # e.g., us-central1

# Model Configuration
SUMMARY_MODEL=                     # e.g., gemini-2.5-flash
GEMINI_MODEL=                      # e.g., gemini-2.0-flash-exp

# Datastore IDs (must include _gcs_store suffix)
CHUNKS_DATASTORE_ID=               # e.g., centef-chunk-data-store_1234_gcs_store
SUMMARIES_DATASTORE_ID=            # e.g., centef-summaries-datastore_5678_gcs_store

# Storage Buckets
SOURCE_BUCKET=                     # e.g., centef-rag-bucket
TARGET_BUCKET=                     # e.g., centef-rag-chunks
CHAT_HISTORY_BUCKET=               # e.g., centef-rag-bucket
CHAT_HISTORY_PATH=chat_history

# Authentication
JWT_SECRET_KEY=                    # Generate with: openssl rand -hex 32
VALID_API_KEYS=                    # Optional: comma-separated API keys
```

- [ ] PROJECT_ID set
- [ ] VERTEX_SEARCH_LOCATION set
- [ ] GENERATION_LOCATION set
- [ ] SUMMARY_MODEL set
- [ ] GEMINI_MODEL set
- [ ] CHUNKS_DATASTORE_ID set (with `_gcs_store` suffix)
- [ ] SUMMARIES_DATASTORE_ID set (with `_gcs_store` suffix)
- [ ] SOURCE_BUCKET set
- [ ] TARGET_BUCKET set
- [ ] CHAT_HISTORY_BUCKET set
- [ ] JWT_SECRET_KEY set (strong random value)

### 7. Sample Users Created
```powershell
cd centef-rag-fresh
python init_users.py
```

- [ ] Admin user created: `admin@centef.org` / `Admin123!`
- [ ] Regular user created: `user@centef.org` / `User123!`
- [ ] User database uploaded to GCS

### 8. Test Data (Optional)
- [ ] Sample documents uploaded to source bucket
- [ ] Documents processed and indexed
- [ ] Manifest contains entries with `status=embedded`

## ☑️ Deployment Steps

### Backend Deployment
```powershell
$env:PROJECT_ID = "your-project-id"
cd centef-rag-fresh
.\deploy-backend.ps1
```

- [ ] Backend Docker image built successfully
- [ ] Backend deployed to Cloud Run
- [ ] Backend URL noted: `_______________________`
- [ ] Health check passed: `/health` returns `{"status":"healthy"}`

### Frontend Deployment
```powershell
.\deploy-frontend.ps1
# Enter backend URL when prompted
```

- [ ] Frontend Docker image built successfully
- [ ] Backend URL updated in `js/auth.js`
- [ ] Frontend deployed to Cloud Run
- [ ] Frontend URL noted: `_______________________`
- [ ] Frontend accessible in browser

## ☑️ Post-Deployment Testing

### 1. Backend API Tests
```powershell
$BACKEND_URL = "your-backend-url"

# Test health
Invoke-RestMethod -Uri "$BACKEND_URL/health"

# Test login
$body = @{email="admin@centef.org"; password="Admin123!"} | ConvertTo-Json
$response = Invoke-RestMethod -Uri "$BACKEND_URL/auth/login" -Method Post -Body $body -ContentType "application/json"
$token = $response.access_token
```

- [ ] Health check returns 200 OK
- [ ] Login succeeds with admin account
- [ ] JWT token received

### 2. Chat Functionality Test
```powershell
$headers = @{Authorization="Bearer $token"; "Content-Type"="application/json"}
$body = @{query="What is counter-terrorism financing?"} | ConvertTo-Json
Invoke-RestMethod -Uri "$BACKEND_URL/chat" -Method Post -Headers $headers -Body $body
```

- [ ] Chat endpoint returns 200 OK
- [ ] Answer includes citations
- [ ] Sources list provided
- [ ] Response time acceptable (<10s)

### 3. Frontend Tests
Open in browser: `your-frontend-url/login.html`

- [ ] Login page loads without errors
- [ ] Can login with admin account
- [ ] Redirects to chat page after login
- [ ] Chat interface displays correctly
- [ ] Can send chat messages
- [ ] Receives AI responses
- [ ] Citations display correctly
- [ ] No console errors (F12 developer tools)

### 4. Admin Features Test
Login as admin, navigate to manifest page:

- [ ] Manifest page loads
- [ ] Can view all documents
- [ ] Can filter by status
- [ ] Can edit document metadata
- [ ] Can approve documents
- [ ] Documents move through workflow states

### 5. Document Upload Test
- [ ] File upload button visible
- [ ] Can select PDF/DOCX file
- [ ] Upload succeeds
- [ ] Document appears in manifest with `pending_processing`
- [ ] Status progresses to `pending_approval` (check logs)

## ☑️ Production Readiness

### Security
- [ ] CORS configured to allow only frontend URL
- [ ] JWT_SECRET_KEY is production-grade (not default)
- [ ] API keys configured (if using VALID_API_KEYS)
- [ ] User passwords are strong
- [ ] Consider moving secrets to Secret Manager

Update CORS in `apps/agent_api/main.py`:
```python
allow_origins=["https://your-frontend-url.a.run.app"]
```

### Monitoring
- [ ] Cloud Run metrics dashboard reviewed
- [ ] Log alerts configured for errors
- [ ] Uptime monitoring enabled (optional)
- [ ] Budget alerts configured

### Performance
- [ ] Backend memory/CPU sufficient (check metrics)
- [ ] Frontend response times acceptable
- [ ] Auto-scaling limits appropriate
- [ ] Cold start times acceptable (or min-instances set)

### Cost Optimization
- [ ] Min-instances = 0 (scales to zero when idle)
- [ ] Max-instances appropriate for expected load
- [ ] Memory/CPU allocations not over-provisioned
- [ ] Budget alerts enabled

### Backup & Recovery
- [ ] GCS buckets have versioning enabled
- [ ] Manifest file backed up regularly
- [ ] User database backed up
- [ ] Rollback procedure tested

## ☑️ Documentation

- [ ] Backend URL documented for team
- [ ] Frontend URL documented for users
- [ ] Sample accounts shared with team
- [ ] Deployment procedure documented
- [ ] Troubleshooting guide reviewed

## 🚨 Common Issues Checklist

If deployment fails, check:

- [ ] PROJECT_ID environment variable set correctly
- [ ] `.env` file exists and has all required variables
- [ ] Datastore IDs include `_gcs_store` suffix
- [ ] APIs enabled in GCP Console
- [ ] Billing account active
- [ ] gcloud authenticated correctly
- [ ] Docker running (for local tests)
- [ ] No firewall blocking gcloud commands

If backend fails:

- [ ] Check Cloud Build logs for build errors
- [ ] Check Cloud Run logs for runtime errors
- [ ] Verify all environment variables set
- [ ] Check GCS bucket permissions
- [ ] Verify Vertex AI API access
- [ ] Test health endpoint: `/health`

If frontend fails:

- [ ] Backend URL correct in `js/auth.js`
- [ ] Frontend can reach backend (check CORS)
- [ ] Static files copied correctly
- [ ] No JavaScript errors in console
- [ ] Backend API responding

## 📊 Success Criteria

Your deployment is successful when:

✅ Backend health check returns 200 OK  
✅ Frontend loads without errors  
✅ Users can login with sample accounts  
✅ Chat queries return AI responses  
✅ Citations appear in responses  
✅ Documents can be uploaded  
✅ Admin can approve documents  
✅ System auto-scales with traffic  
✅ No errors in Cloud Run logs  
✅ Costs within expected range  

## 📞 Need Help?

### Documentation
- [CLOUD_RUN_DEPLOYMENT.md](CLOUD_RUN_DEPLOYMENT.md) - Full deployment guide
- [CLOUD_RUN_QUICK_REF.md](CLOUD_RUN_QUICK_REF.md) - Quick reference
- [CLOUD_RUN_WORKFLOW.md](CLOUD_RUN_WORKFLOW.md) - Visual workflow

### Logs & Debugging
```powershell
# Backend logs
gcloud run services logs tail centef-rag-api --region us-central1

# Frontend logs
gcloud run services logs tail centef-rag-frontend --region us-central1

# Cloud Build logs
gcloud builds list --limit 10
```

### Support Channels
- Check Cloud Run logs for detailed errors
- Review Cloud Build history in GCP Console
- Test locally with `.\test-docker-local.ps1`
- Verify environment variables with `gcloud run services describe`

---

**Print this checklist** and check off items as you complete them. Keep backend and frontend URLs documented for future reference.

**Ready to deploy?** Start with: `$env:PROJECT_ID = "your-project-id"` then run `.\deploy-backend.ps1`
