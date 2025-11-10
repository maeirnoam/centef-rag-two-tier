# CENTEF RAG - Cloud Run Deployment Summary

## 📦 Files Created for Cloud Run Deployment

### Docker Configuration
- ✅ `apps/agent_api/Dockerfile` - Backend API container
- ✅ `apps/agent_api/.dockerignore` - Backend build exclusions
- ✅ `apps/frontend/Dockerfile` - Frontend container
- ✅ `apps/frontend/.dockerignore` - Frontend build exclusions

### Deployment Scripts
- ✅ `deploy-backend.ps1` - Automated backend deployment to Cloud Run
- ✅ `deploy-frontend.ps1` - Automated frontend deployment to Cloud Run
- ✅ `test-docker-local.ps1` - Local Docker testing before deployment

### Documentation
- ✅ `CLOUD_RUN_DEPLOYMENT.md` - Complete deployment guide
- ✅ `CLOUD_RUN_QUICK_REF.md` - Quick reference for common tasks
- ✅ `DEPLOYMENT_SUMMARY.md` - This file

### Code Updates
- ✅ `apps/frontend/serve.py` - Updated to use PORT environment variable
- ✅ `apps/frontend/js/auth.js` - Added comment for Cloud Run URL update
- ✅ `requirements.txt` - Added gunicorn for production server

## 🚀 Deployment Workflow

### Phase 1: Local Testing (Optional)
```powershell
.\test-docker-local.ps1
```
This builds and runs both containers locally to verify everything works.

### Phase 2: Deploy Backend
```powershell
$env:PROJECT_ID = "your-project-id"
.\deploy-backend.ps1
```
Output: Backend API URL (e.g., `https://centef-rag-api-abc123-uc.a.run.app`)

### Phase 3: Deploy Frontend
```powershell
.\deploy-frontend.ps1
```
When prompted, enter the backend URL from Phase 2.

Output: Frontend URL (e.g., `https://centef-rag-frontend-abc123-uc.a.run.app`)

### Phase 4: Test Production
1. Open frontend URL in browser
2. Login with sample accounts
3. Test chat functionality
4. Test document upload
5. Test admin features (if admin)

## 🎯 Key Features

### Backend Container
- **Base Image**: Python 3.11-slim
- **Web Server**: Gunicorn + Uvicorn workers
- **Port**: 8080 (Cloud Run standard)
- **Resources**: 2GB RAM, 2 CPUs
- **Timeout**: 300 seconds
- **Auto-scaling**: 0-10 instances
- **Environment**: All variables from `.env`

### Frontend Container
- **Base Image**: Python 3.11-slim
- **Web Server**: Python HTTP server
- **Port**: 8080 (Cloud Run standard)
- **Resources**: 512MB RAM, 1 CPU
- **Timeout**: 60 seconds
- **Auto-scaling**: 0-5 instances
- **CORS**: Enabled for backend communication

## 🔧 What Changed

### 1. Backend (apps/agent_api/)
**Added**:
- `Dockerfile` - Multi-stage build optimized for Cloud Run
- `.dockerignore` - Excludes unnecessary files from image

**Changed**:
- None - backend was already Cloud Run compatible

### 2. Frontend (apps/frontend/)
**Added**:
- `Dockerfile` - Lightweight static file server
- `.dockerignore` - Minimal exclusions

**Changed**:
- `serve.py` - Now reads PORT from environment variable
- `js/auth.js` - Added comment about updating API_BASE_URL

### 3. Dependencies (requirements.txt)
**Added**:
- `gunicorn==21.2.0` - Production WSGI server

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Google Cloud Run                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────┐      ┌──────────────────────┐   │
│  │  Frontend Container  │      │  Backend Container   │   │
│  │  Port: 8080          │─────▶│  Port: 8080          │   │
│  │  Image: ...frontend  │      │  Image: ...api       │   │
│  │  Memory: 512Mi       │      │  Memory: 2Gi         │   │
│  └──────────────────────┘      └──────────────────────┘   │
│         │                                  │               │
│         │                                  │               │
│         ▼                                  ▼               │
│  Static Files (HTML/CSS/JS)     FastAPI Application       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                                   │
                                   │
                                   ▼
        ┌──────────────────────────────────────────┐
        │         Google Cloud Services            │
        ├──────────────────────────────────────────┤
        │  • Cloud Storage (GCS)                   │
        │  • Vertex AI Search                      │
        │  • Vertex AI (Gemini)                    │
        │  • Discovery Engine                      │
        └──────────────────────────────────────────┘
```

## 🔐 Security Configuration

### Authentication Flow
1. User enters credentials on frontend
2. Frontend sends POST to `/auth/login`
3. Backend validates credentials
4. Backend returns JWT token
5. Frontend stores token in localStorage
6. All subsequent requests include: `Authorization: Bearer <token>`

### Environment Variables
Sensitive data (JWT_SECRET_KEY, etc.) is passed to Cloud Run as environment variables, not baked into the container image.

### CORS Configuration
Backend allows frontend origin. For production, update `main.py`:
```python
allow_origins=["https://your-frontend-url.a.run.app"]
```

## 💰 Cost Estimate

### Monthly Costs (Low Usage)
Assuming 1000 requests/day:

**Backend API**:
- Requests: 1000/day × 30 days × $0.00002448 = $0.73
- CPU time: ~50 hours × $0.024 = $1.20
- Memory: Included with CPU
- **Total**: ~$2/month

**Frontend**:
- Requests: 1000/day × 30 days × $0.00001632 = $0.49
- CPU time: ~10 hours × $0.024 = $0.24
- **Total**: ~$0.73/month

**Other Services** (unchanged):
- Cloud Storage: ~$1-5/month
- Vertex AI Search: Usage-based
- Gemini API: Usage-based

**Total Cloud Run Cost**: ~$3-5/month for low usage

**Free Tier**: Cloud Run includes 2 million requests/month free!

## 🧪 Testing Checklist

### Pre-Deployment Testing
- [ ] `.env` file configured with production values
- [ ] Sample users created (`init_users.py`)
- [ ] GCS buckets exist and are accessible
- [ ] Vertex AI Search datastores configured
- [ ] Local Docker test passes (`test-docker-local.ps1`)

### Post-Deployment Testing
- [ ] Backend health check returns `{"status":"healthy"}`
- [ ] Login works with sample accounts
- [ ] Chat endpoint returns AI responses with citations
- [ ] File upload succeeds
- [ ] Admin can view manifest
- [ ] Admin can approve documents
- [ ] Documents become searchable after approval
- [ ] Frontend loads without errors
- [ ] CORS allows frontend ↔ backend communication

## 📚 Documentation Index

For detailed information, see:

1. **`CLOUD_RUN_DEPLOYMENT.md`** - Complete deployment guide
   - Prerequisites
   - Step-by-step deployment
   - Configuration details
   - Testing procedures
   - Troubleshooting

2. **`CLOUD_RUN_QUICK_REF.md`** - Quick reference
   - Common commands
   - Quick fixes
   - Monitoring
   - Cost management

3. **`README.md`** - Main project documentation
   - System architecture
   - Local development setup
   - Core functionality

4. **`QUICK_START_FRONTEND.md`** - Frontend usage guide
   - User workflows
   - Login credentials
   - Feature descriptions

5. **`ADMIN_GUIDE.md`** - Admin features
   - Document approval workflow
   - User management
   - System administration

## 🔄 Update Workflow

When you make changes to the code:

1. **Test locally first**:
   ```powershell
   .\start_local.ps1  # or use test-docker-local.ps1
   ```

2. **Deploy backend** (if backend changed):
   ```powershell
   .\deploy-backend.ps1
   ```

3. **Deploy frontend** (if frontend changed):
   ```powershell
   .\deploy-frontend.ps1
   ```

4. **Verify deployment**:
   - Check logs: `gcloud run services logs read <service-name>`
   - Test endpoints
   - Monitor for errors

5. **Rollback if needed**:
   ```powershell
   gcloud run services update-traffic <service-name> --to-revisions <previous-revision>=100
   ```

## 🆘 Getting Help

### Logs
```powershell
# Backend
gcloud run services logs tail centef-rag-api --region us-central1

# Frontend
gcloud run services logs tail centef-rag-frontend --region us-central1
```

### Service Details
```powershell
gcloud run services describe centef-rag-api --region us-central1
```

### Common Issues
See **Troubleshooting** section in `CLOUD_RUN_DEPLOYMENT.md`

## ✅ Deployment Checklist

### Before Deployment
- [ ] GCP project created and billing enabled
- [ ] Required APIs enabled
- [ ] `gcloud` CLI installed and authenticated
- [ ] `.env` file configured
- [ ] `PROJECT_ID` environment variable set

### During Deployment
- [ ] Backend deployment succeeds
- [ ] Backend URL captured
- [ ] Frontend deployment succeeds with backend URL
- [ ] No deployment errors in Cloud Build logs

### After Deployment
- [ ] Health check passes
- [ ] Login works
- [ ] Chat functionality works
- [ ] Document upload works
- [ ] Admin features work (if applicable)
- [ ] No errors in Cloud Run logs

## 🎉 Success Criteria

Your deployment is successful when:

1. ✅ Backend health endpoint returns 200 OK
2. ✅ Frontend loads without console errors
3. ✅ Users can login and chat
4. ✅ AI responses include citations
5. ✅ Documents can be uploaded and indexed
6. ✅ Admin can approve documents
7. ✅ System scales automatically with traffic
8. ✅ Costs stay within expected range

## 📞 Next Steps

After successful deployment:

1. **Update DNS** (optional) - Point custom domain to Cloud Run services
2. **Set up monitoring** - Configure alerts for errors/latency
3. **Enable logging** - Set up log exports for analysis
4. **Configure secrets** - Move sensitive data to Secret Manager
5. **Optimize costs** - Adjust resources based on actual usage
6. **Set up CI/CD** - Automate deployments with Cloud Build triggers

---

**Questions?** See `CLOUD_RUN_DEPLOYMENT.md` for detailed guidance.
