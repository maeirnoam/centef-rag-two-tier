# CENTEF RAG - Cloud Run Quick Reference

## 🚀 Quick Deployment Commands

### Prerequisites
```powershell
# Set your project ID
$env:PROJECT_ID = "your-project-id"

# Verify authentication
gcloud auth list
gcloud config get-value project
```

### Deploy Backend
```powershell
cd centef-rag-fresh
.\deploy-backend.ps1
```

### Deploy Frontend
```powershell
.\deploy-frontend.ps1
# When prompted, enter backend URL from previous step
```

## 🔗 Service URLs

After deployment, you'll get:

**Backend API**: `https://centef-rag-api-[hash]-uc.a.run.app`
**Frontend**: `https://centef-rag-frontend-[hash]-uc.a.run.app`

## 📋 Key Endpoints

### Backend API
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/auth/login` | POST | No | User login |
| `/auth/register` | POST | No | User registration |
| `/chat` | POST | Yes | Send chat query |
| `/chat/sessions` | GET | Yes | List user sessions |
| `/manifest` | GET | No | List documents |
| `/upload` | POST | Yes | Upload document |
| `/admin/manifest/pending` | GET | Admin | Pending approvals |

### Frontend Pages
| Page | URL | Access |
|------|-----|--------|
| Login | `/login.html` | Public |
| Chat | `/chat.html` | Authenticated |
| Manifest | `/manifest.html` | Admin only |
| Users | `/users.html` | Admin only |

## 🔧 Quick Configuration Changes

### Update Backend Environment Variables
```powershell
gcloud run services update centef-rag-api `
  --update-env-vars KEY=VALUE `
  --region us-central1
```

### Update Backend Resources
```powershell
# Increase memory
gcloud run services update centef-rag-api `
  --memory 4Gi `
  --region us-central1

# Increase timeout
gcloud run services update centef-rag-api `
  --timeout 600 `
  --region us-central1

# Set minimum instances (reduces cold starts, increases cost)
gcloud run services update centef-rag-api `
  --min-instances 1 `
  --region us-central1
```

### View Service Details
```powershell
# Get service URL
gcloud run services describe centef-rag-api `
  --region us-central1 `
  --format "value(status.url)"

# View all settings
gcloud run services describe centef-rag-api `
  --region us-central1
```

## 📊 Monitoring Commands

### View Logs
```powershell
# Stream backend logs
gcloud run services logs tail centef-rag-api --region us-central1

# Stream frontend logs
gcloud run services logs tail centef-rag-frontend --region us-central1

# Read last 100 lines
gcloud run services logs read centef-rag-api --region us-central1 --limit 100
```

### Check Service Status
```powershell
# List all Cloud Run services
gcloud run services list --region us-central1

# Get service details
gcloud run services describe centef-rag-api --region us-central1
```

### View Metrics
Open in browser:
```
https://console.cloud.google.com/run/detail/us-central1/centef-rag-api/metrics
```

## 🔄 Update & Rollback

### Redeploy Services
```powershell
# Rebuild and deploy backend
.\deploy-backend.ps1

# Rebuild and deploy frontend
.\deploy-frontend.ps1
```

### Rollback to Previous Version
```powershell
# List revisions
gcloud run revisions list --service centef-rag-api --region us-central1

# Rollback to specific revision
gcloud run services update-traffic centef-rag-api `
  --to-revisions REVISION_NAME=100 `
  --region us-central1
```

### Delete Services
```powershell
# Delete backend
gcloud run services delete centef-rag-api --region us-central1

# Delete frontend
gcloud run services delete centef-rag-frontend --region us-central1
```

## 🧪 Testing Commands

### Test Backend Health
```powershell
$BACKEND_URL = "https://centef-rag-api-abc123-uc.a.run.app"
Invoke-RestMethod -Uri "$BACKEND_URL/health"
```

### Test Login
```powershell
$body = @{
    email = "admin@centef.org"
    password = "Admin123!"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$BACKEND_URL/auth/login" -Method Post -Body $body -ContentType "application/json"
```

### Test Chat (requires token from login)
```powershell
$headers = @{
    "Authorization" = "Bearer YOUR_TOKEN_HERE"
    "Content-Type" = "application/json"
}

$body = @{
    query = "What is counter-terrorism financing?"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$BACKEND_URL/chat" -Method Post -Headers $headers -Body $body
```

## 🔒 Security Commands

### Create Secret in Secret Manager
```powershell
# Create secret
echo "your-secret-value" | gcloud secrets create secret-name --data-file=-

# Grant Cloud Run access
$PROJECT_NUMBER = gcloud projects describe $env:PROJECT_ID --format="value(projectNumber)"
gcloud secrets add-iam-policy-binding secret-name `
  --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"

# Update service to use secret
gcloud run services update centef-rag-api `
  --update-secrets=ENV_VAR_NAME=secret-name:latest `
  --region us-central1
```

### Update CORS Settings
Edit `apps/agent_api/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-url.a.run.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Then redeploy:
```powershell
.\deploy-backend.ps1
```

## 💰 Cost Management

### Check Current Costs
```
https://console.cloud.google.com/billing
```

### Scale to Zero (No Cost When Idle)
```powershell
# Verify min-instances is 0 (default)
gcloud run services describe centef-rag-api `
  --region us-central1 `
  --format "value(spec.template.spec.containers[0].resources.limits)"
```

### Reduce Costs
```powershell
# Lower memory/CPU
gcloud run services update centef-rag-api `
  --memory 1Gi `
  --cpu 1 `
  --region us-central1

# Reduce max instances
gcloud run services update centef-rag-api `
  --max-instances 5 `
  --region us-central1
```

## 🐛 Troubleshooting Quick Fixes

### Backend Returns 500 Errors
```powershell
# Check logs for errors
gcloud run services logs read centef-rag-api --region us-central1 --limit 50

# Check environment variables
gcloud run services describe centef-rag-api `
  --region us-central1 `
  --format "value(spec.template.spec.containers[0].env)"
```

### Frontend Can't Connect to Backend
1. Check CORS settings in `main.py`
2. Verify API_BASE_URL in `js/auth.js`
3. Check backend logs for CORS errors

### Cold Start Too Slow
```powershell
# Set min instances to 1 (increases cost)
gcloud run services update centef-rag-api `
  --min-instances 1 `
  --region us-central1
```

### Out of Memory
```powershell
# Increase memory limit
gcloud run services update centef-rag-api `
  --memory 4Gi `
  --region us-central1
```

## 📞 Useful Links

- Cloud Run Console: https://console.cloud.google.com/run
- Cloud Build History: https://console.cloud.google.com/cloud-build/builds
- IAM Permissions: https://console.cloud.google.com/iam-admin/iam
- Logs Explorer: https://console.cloud.google.com/logs/query

## 📝 Sample Accounts

After deploying, test with these accounts:

**Admin Account** (full access):
- Email: `admin@centef.org`
- Password: `Admin123!`

**Regular User** (chat only):
- Email: `user@centef.org`
- Password: `User123!`

## 🎯 Common Tasks

### Task: Update Environment Variable
```powershell
gcloud run services update centef-rag-api `
  --update-env-vars SUMMARY_MODEL=gemini-2.0-flash `
  --region us-central1
```

### Task: View Service Logs in Real-Time
```powershell
gcloud run services logs tail centef-rag-api --region us-central1
```

### Task: Check Service Health
```powershell
$url = gcloud run services describe centef-rag-api --region us-central1 --format "value(status.url)"
Invoke-RestMethod -Uri "$url/health"
```

### Task: Scale Service
```powershell
gcloud run services update centef-rag-api `
  --max-instances 20 `
  --concurrency 100 `
  --region us-central1
```
