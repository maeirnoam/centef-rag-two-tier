# Frontend Deployment Guide

## Quick Start

### 1. Start the Backend API Server

```powershell
cd centef-rag-two-tier\apps\agent_api
python main.py
```

The API will be available at: **http://localhost:8000**

### 2. Start the Frontend Server

Open a **new terminal** and run:

```powershell
cd centef-rag-two-tier\apps\frontend
python serve.py
```

The frontend will be available at: **http://localhost:3000**

### 3. Access the Application

Open your browser to:
- **Login:** http://localhost:3000/login.html
- **Chat:** http://localhost:3000/chat.html
- **Manifest:** http://localhost:3000/manifest.html (admin only)

## Sample User Accounts

### Admin Account
- **Email:** admin@centef.org
- **Password:** Admin123!
- **Roles:** admin, user
- **Capabilities:** 
  - Chat with RAG system
  - Upload documents
  - View and edit manifest
  - Approve documents for indexing

### Regular User Account
- **Email:** user@centef.org
- **Password:** User123!
- **Roles:** user
- **Capabilities:**
  - Chat with RAG system
  - Upload documents
  - View own chat history

## Features

### Chat Interface (`chat.html`)
- **Chat Sessions:** Create and manage multiple conversation sessions
- **Message History:** All conversations are automatically saved per user
- **File Upload:** Drag & drop or browse to upload documents (PDF, DOCX, images, SRT)
- **Source Citations:** See which documents were used to answer your questions
- **Session Management:** Rename, view, and delete chat sessions

### Manifest Management (`manifest.html`) - Admin Only
- **View All Documents:** See all documents in the system with status badges
- **Filter by Status:** Filter documents by processing stage
- **Edit Metadata:** Update document title, author, organization, date, publisher, tags
- **Approve Documents:** Review and approve documents pending approval
- **Automatic Indexing:** Approved documents automatically enter the indexing pipeline

## File Upload Workflow

1. **User uploads file** via chat interface sidebar
2. File is uploaded to `gs://{SOURCE_BUCKET}/uploads/{source_id}/`
3. Manifest entry created with status: `pending_processing`
4. Processing pipeline picks up the file automatically
5. After summarization, status changes to `pending_approval`
6. **Admin reviews and approves** the metadata in manifest page
7. Status changes to `pending_embedding` → triggers indexing
8. Once indexed, status changes to `embedded`
9. Document is now searchable in chat queries

## Architecture

### Frontend Stack
- **HTML/CSS/JavaScript** - No build step required
- **Vanilla JavaScript** - No framework dependencies
- **JWT Authentication** - Token stored in localStorage
- **CORS-enabled** - Backend allows requests from localhost:3000

### Backend API
- **FastAPI** - Python async web framework
- **JWT Tokens** - 60-minute expiration (configurable)
- **Role-Based Access Control** - Admin vs. user permissions
- **Google Cloud Storage** - File storage and chat history
- **Vertex AI Search** - Two-tier RAG retrieval
- **Gemini AI** - Answer synthesis with citations

## API Endpoints

### Authentication
- `POST /auth/login` - Login with email/password → returns JWT token
- `POST /auth/register` - Register new user (if enabled)
- `GET /auth/me` - Get current user info

### Chat
- `POST /chat` - Send query and get AI response
- `GET /chat/sessions` - List user's chat sessions
- `GET /chat/history/{session_id}` - Get conversation messages
- `POST /chat/sessions` - Create new session
- `DELETE /chat/sessions/{session_id}` - Delete session
- `PATCH /chat/sessions/{session_id}/title` - Update session title

### Manifest
- `GET /manifest` - List all documents (optional `?status=` filter)
- `PUT /manifest/{source_id}` - Update document metadata
- `POST /manifest` - Create new manifest entry

### Upload
- `POST /upload` - Upload file (requires authentication)

### Admin (Requires `admin` role)
- `GET /admin/manifest/pending` - Get documents pending approval
- `PUT /admin/manifest/{source_id}/approve` - Approve/reject document
- `GET /admin/stats` - System statistics
- `GET /admin/users` - List all users

## Customization

### Change API URL
Edit `js/auth.js`:
```javascript
const API_BASE_URL = 'http://localhost:8000';  // Change this
```

### Change Frontend Port
Edit `serve.py`:
```python
PORT = 3000  # Change this
```

### Adjust JWT Expiration
Edit `.env`:
```bash
JWT_EXPIRATION_MINUTES=60  # Change this
```

### Configure CORS
Edit `apps/agent_api/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Restrict origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Troubleshooting

### Backend won't start
```powershell
# Check Python environment
conda activate .conda

# Check if port 8000 is in use
netstat -ano | findstr :8000

# Check required environment variables
python centef-rag-two-tier\check_env.py
```

### Frontend won't connect to backend
1. Verify backend is running: http://localhost:8000/health
2. Check CORS settings in `main.py`
3. Check browser console for errors (F12)
4. Verify API_BASE_URL in `js/auth.js`

### Login fails
1. Verify users exist: `python centef-rag-two-tier\shared\user_management.py list`
2. Check credentials: admin@centef.org / Admin123!
3. Check browser console for detailed error
4. Verify JWT_SECRET_KEY is set in `.env`

### File upload fails
1. Check GCS authentication: `gcloud auth application-default login`
2. Verify SOURCE_BUCKET in `.env`
3. Check file type is supported (PDF, DOCX, images, SRT)
4. Check browser console for error details

### Chat doesn't show sources
1. Verify documents are indexed (status=`embedded` in manifest)
2. Check that datastores are populated:
   ```powershell
   python centef-rag-two-tier\list_chunks.py
   python centef-rag-two-tier\list_summaries.py
   ```
3. Try a query about known document content

## Production Deployment Notes

### Security Checklist
- [ ] Change default user passwords
- [ ] Generate secure JWT secret: `openssl rand -hex 32`
- [ ] Restrict CORS origins to your domain
- [ ] Enable HTTPS/TLS
- [ ] Set up rate limiting on authentication endpoints
- [ ] Implement bcrypt password hashing (currently SHA-256)
- [ ] Add audit logging for admin actions
- [ ] Configure firewall rules for GCP resources

### Performance Optimization
- [ ] Use a production ASGI server (Gunicorn + Uvicorn)
- [ ] Add Redis for session caching
- [ ] Implement query response caching
- [ ] Set up Cloud CDN for static files
- [ ] Enable gzip compression
- [ ] Add connection pooling for GCS

### Monitoring
- [ ] Set up Cloud Logging for API access logs
- [ ] Configure Cloud Monitoring for uptime checks
- [ ] Add error tracking (Sentry, etc.)
- [ ] Monitor token usage for Gemini API
- [ ] Track user activity metrics

## Development Workflow

### Adding New Features
1. Backend: Add endpoint to `apps/agent_api/main.py`
2. Frontend: Add UI in relevant HTML file
3. API calls: Use `apiCall()` helper from `js/auth.js`
4. Test with both admin and regular user accounts

### Updating Styles
Edit `css/style.css` - changes apply immediately (no build step)

### Debugging
- **Backend logs:** Check terminal where `main.py` is running
- **Frontend logs:** Open browser DevTools (F12) → Console tab
- **API requests:** DevTools → Network tab
- **Authentication:** Check localStorage in DevTools → Application tab

## File Structure

```
apps/
├── agent_api/
│   └── main.py              # FastAPI backend
└── frontend/
    ├── serve.py             # Development HTTP server
    ├── login.html           # Login page
    ├── chat.html            # Chat interface
    ├── manifest.html        # Manifest management (admin)
    ├── css/
    │   └── style.css        # Shared styles
    └── js/
        └── auth.js          # Authentication utilities
```

## Next Steps

1. **Test the workflow:** Login → Upload file → Admin approves → Chat queries
2. **Customize branding:** Update colors, logo, and title in HTML/CSS
3. **Add more features:** User profile page, advanced search filters, etc.
4. **Deploy to production:** Follow security checklist above
