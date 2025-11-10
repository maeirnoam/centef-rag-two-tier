# CENTEF RAG - Cloud Run Deployment Workflow

## 📊 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Your Local Machine                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────┐         ┌──────────────────────────────┐      │
│  │   Source Code  │────────▶│  Deploy Scripts (PowerShell) │      │
│  │   + .env file  │         │  • deploy-backend.ps1         │      │
│  │   + Dockerfile │         │  • deploy-frontend.ps1        │      │
│  └────────────────┘         └──────────────────────────────┘      │
│                                         │                           │
└─────────────────────────────────────────┼───────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Google Cloud Build                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────┐         ┌─────────────────────┐          │
│  │  Build Backend      │         │  Build Frontend     │          │
│  │  Docker Image       │         │  Docker Image       │          │
│  │                     │         │                     │          │
│  │  • Install deps     │         │  • Copy static      │          │
│  │  • Copy code        │         │    files            │          │
│  │  • Configure        │         │  • Configure        │          │
│  │    gunicorn         │         │    server           │          │
│  └─────────────────────┘         └─────────────────────┘          │
│           │                                │                        │
│           ▼                                ▼                        │
│  ┌─────────────────────┐         ┌─────────────────────┐          │
│  │ Push to Container   │         │ Push to Container   │          │
│  │ Registry (GCR)      │         │ Registry (GCR)      │          │
│  └─────────────────────┘         └─────────────────────┘          │
│           │                                │                        │
└───────────┼────────────────────────────────┼────────────────────────┘
            │                                │
            ▼                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Google Cloud Run                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐│
│  │  Backend Service             │  │  Frontend Service            ││
│  │  centef-rag-api              │  │  centef-rag-frontend         ││
│  ├──────────────────────────────┤  ├──────────────────────────────┤│
│  │  • FastAPI + Gunicorn        │  │  • Python HTTP Server        ││
│  │  • Port: 8080                │  │  • Port: 8080                ││
│  │  • Memory: 2Gi               │  │  • Memory: 512Mi             ││
│  │  • CPU: 2                    │  │  • CPU: 1                    ││
│  │  • Auto-scale: 0-10          │  │  • Auto-scale: 0-5           ││
│  │  • Timeout: 300s             │  │  • Timeout: 60s              ││
│  │                              │  │                              ││
│  │  Environment Variables:      │  │  • Serves HTML/CSS/JS        ││
│  │  • PROJECT_ID                │  │  • CORS enabled              ││
│  │  • VERTEX_SEARCH_LOCATION    │  │  • Static file server        ││
│  │  • DATASTORE_IDs             │  │                              ││
│  │  • JWT_SECRET_KEY            │  │                              ││
│  │  • Bucket names              │  │                              ││
│  └──────────────────────────────┘  └──────────────────────────────┘│
│           │                                    │                    │
│           │                                    │                    │
│           │  ┌────────────────────────┐       │                    │
│           │  │  Public HTTPS URLs     │       │                    │
│           └─▶│  - Backend API         │◀──────┘                    │
│              │  - Frontend Web        │                            │
│              └────────────────────────┘                            │
│                         │                                           │
└─────────────────────────┼───────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Google Cloud Services                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │  Cloud Storage  │  │  Vertex AI      │  │  Discovery      │   │
│  │  (GCS)          │  │  (Gemini)       │  │  Engine         │   │
│  │                 │  │                 │  │  (Search)       │   │
│  │  • Documents    │  │  • Summarize    │  │  • Chunks       │   │
│  │  • Chunks       │  │  • Synthesize   │  │  • Summaries    │   │
│  │  • Summaries    │  │  • Extract      │  │  • Full-text    │   │
│  │  • Manifest     │  │    metadata     │  │    search       │   │
│  │  • Chat history │  │                 │  │                 │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔄 Deployment Flow

### Step 1: Prepare Environment
```powershell
# Set project ID
$env:PROJECT_ID = "your-project-id"

# Authenticate
gcloud auth login
gcloud config set project $env:PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

### Step 2: Deploy Backend
```powershell
.\deploy-backend.ps1
```

**What happens:**
1. Script reads `.env` file
2. Navigates to `apps/agent_api/`
3. Cloud Build creates Docker image from `Dockerfile`
4. Image pushed to Container Registry (GCR)
5. Cloud Run creates service from image
6. Environment variables set from `.env`
7. Service receives public HTTPS URL
8. Health check verifies deployment

**Output:**
```
API Endpoints:
  Base URL: https://centef-rag-api-abc123-uc.a.run.app
  Health:   https://centef-rag-api-abc123-uc.a.run.app/health
```

### Step 3: Deploy Frontend
```powershell
.\deploy-frontend.ps1
```

**Prompt:** Enter backend URL from Step 2

**What happens:**
1. Updates `js/auth.js` with backend URL
2. Navigates to `apps/frontend/`
3. Cloud Build creates Docker image
4. Image pushed to Container Registry
5. Cloud Run creates service from image
6. Service receives public HTTPS URL
7. Frontend can now communicate with backend

**Output:**
```
Application URLs:
  Frontend: https://centef-rag-frontend-xyz789-uc.a.run.app
  Login:    https://centef-rag-frontend-xyz789-uc.a.run.app/login.html
```

## 🌐 Request Flow

### User Login Flow
```
User Browser
    │
    │ 1. GET /login.html
    ▼
Frontend Service (Cloud Run)
    │
    │ 2. Serve login page
    ▼
User Browser
    │
    │ 3. POST /auth/login {email, password}
    ▼
Backend Service (Cloud Run)
    │
    │ 4. Validate credentials
    │ 5. Generate JWT token
    ▼
User Browser (stores token in localStorage)
```

### Chat Query Flow
```
User Browser
    │
    │ 1. POST /chat {query, token}
    ▼
Backend Service (Cloud Run)
    │
    │ 2. Validate JWT token
    │ 3. Save user message to GCS
    ▼
Vertex AI Search (Discovery Engine)
    │
    │ 4. Search summaries datastore
    │ 5. Search chunks datastore
    ▼
Backend Service
    │
    │ 6. Combine search results
    ▼
Vertex AI (Gemini)
    │
    │ 7. Generate answer with citations
    ▼
Backend Service
    │
    │ 8. Save assistant response to GCS
    │ 9. Return answer with sources
    ▼
User Browser (displays answer + citations)
```

### Document Upload Flow
```
User Browser
    │
    │ 1. POST /upload {file, token}
    ▼
Backend Service (Cloud Run)
    │
    │ 2. Validate JWT token
    │ 3. Upload file to GCS
    │ 4. Create manifest entry
    │ 5. Queue background processing
    ▼
Cloud Storage (GCS)
    │
    │ Files stored in sources/
    ▼
Background Processing (async)
    │
    │ 6. Extract text from PDF/DOCX
    │ 7. Create chunks
    ▼
Vertex AI (Gemini)
    │
    │ 8. Generate summary
    │ 9. Extract metadata
    ▼
Cloud Storage (GCS)
    │
    │ 10. Save chunks and summary
    │ 11. Update manifest: status=pending_approval
    ▼
Admin Approval (via manifest.html)
    │
    │ 12. Admin reviews metadata
    │ 13. Clicks "Approve"
    ▼
Backend Service
    │
    │ 14. Update status: pending_embedding
    │ 15. Trigger indexing
    ▼
Discovery Engine
    │
    │ 16. Index chunks
    │ 17. Index summary
    │ 18. Update status: embedded
    ▼
Document is now searchable in chat queries
```

## 🔐 Security Flow

### Authentication
```
1. User submits credentials
2. Backend validates against user database (GCS)
3. Backend generates JWT token with user_id + roles
4. Frontend stores token in localStorage
5. All API calls include: Authorization: Bearer <token>
6. Backend validates token on each request
7. Backend checks user roles for admin endpoints
```

### Data Protection
```
In Transit:
  • All connections use HTTPS (TLS 1.3)
  • Cloud Run provides automatic SSL certificates
  • JWT tokens encrypted

At Rest:
  • GCS buckets encrypted by default
  • User passwords hashed with bcrypt
  • JWT secret stored as environment variable
```

## 📊 Scaling Behavior

### Auto-Scaling
```
Low Traffic (0-10 requests/sec):
  Backend:  0-1 instances (scales to zero)
  Frontend: 0-1 instances

Medium Traffic (10-100 requests/sec):
  Backend:  2-5 instances
  Frontend: 1-2 instances

High Traffic (100+ requests/sec):
  Backend:  5-10 instances (max)
  Frontend: 2-5 instances (max)

Each instance can handle:
  Backend:  ~80 concurrent requests
  Frontend: ~80 concurrent requests
```

### Cold Start Optimization
```
First request after idle:
  ├─ Container startup: ~5-10s
  ├─ Import dependencies: ~2-5s
  ├─ Initialize connections: ~1-2s
  └─ Total: ~10-15s

Subsequent requests (warm):
  └─ Response time: <100ms

To eliminate cold starts:
  gcloud run services update centef-rag-api \
    --min-instances 1 \
    --region us-central1
```

## 💰 Cost Breakdown

### Free Tier (First 2 million requests/month)
```
Backend + Frontend combined:
  Requests: FREE for first 2M
  CPU time: $0.024/vCPU-hour
  Memory: $0.0025/GiB-hour
  
Example (1000 requests/day):
  • 30K requests/month: FREE
  • CPU time: ~60 hours/month × $0.024 = $1.44
  • Memory: Included with CPU
  
Total: ~$1.50/month
```

### Beyond Free Tier
```
Each additional million requests:
  Backend:  $0.40
  Frontend: $0.40
  
Example (1M requests/month):
  • Requests: FREE (under 2M)
  • CPU time: ~200 hours × $0.024 = $4.80
  • Memory: Included
  
Total: ~$5/month
```

## 🔄 Update Workflow

### Code Change ➜ Production

```powershell
# 1. Make changes to code
code apps/agent_api/main.py

# 2. Test locally (optional)
.\start_local.ps1

# 3. Deploy to Cloud Run
.\deploy-backend.ps1

# Cloud Run automatically:
#   • Builds new image
#   • Creates new revision
#   • Routes traffic gradually
#   • Keeps old revision as backup
```

### Zero-Downtime Deployment
```
Cloud Run handles this automatically:

Current version (v1): 100% traffic
    │
    │ Deploy new version
    ▼
Traffic split:
    v1: 80% traffic  ──┐
    v2: 20% traffic  ──┤ Health checks
                       │
    v1: 50% traffic  ──┤ No errors?
    v2: 50% traffic  ──┤ Continue...
                       │
    v1: 0% traffic   ──┤
    v2: 100% traffic ──┘ Complete!
```

## 🧪 Testing Strategy

### Local Testing
```powershell
# Test with Docker locally
.\test-docker-local.ps1

# Verifies:
  ✓ Docker images build successfully
  ✓ Containers start without errors
  ✓ Health checks pass
  ✓ Frontend serves files
  ✓ Backend API responds
```

### Staging Environment
```powershell
# Deploy to staging project
$env:PROJECT_ID = "centef-rag-staging"
.\deploy-backend.ps1
.\deploy-frontend.ps1

# Run integration tests
python test_rag_pipeline.py
python test_chat_history.py
```

### Production Deployment
```powershell
# Deploy to production project
$env:PROJECT_ID = "centef-rag-production"
.\deploy-backend.ps1
.\deploy-frontend.ps1

# Monitor logs for errors
gcloud run services logs tail centef-rag-api
```

## 📚 Related Documentation

- **[CLOUD_RUN_DEPLOYMENT.md](CLOUD_RUN_DEPLOYMENT.md)** - Complete deployment guide
- **[CLOUD_RUN_QUICK_REF.md](CLOUD_RUN_QUICK_REF.md)** - Quick reference commands
- **[DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)** - Files created and changes made

---

**Ready to deploy?** Run `.\deploy-backend.ps1` to get started!
