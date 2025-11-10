# CENTEF RAG System - Quick Start

## 🚀 One-Command Startup

```powershell
cd centef-rag-two-tier
.\start_local.ps1
```

This will:
1. ✅ Start the backend API on http://localhost:8000
2. ✅ Start the frontend on http://localhost:3000
3. ✅ Open your browser to the login page

## 👤 Login Credentials

**Admin Account** (full access):
- Email: `admin@centef.org`
- Password: `Admin123!`

**Regular User** (chat only):
- Email: `user@centef.org`  
- Password: `User123!`

## 📱 Pages

| Page | URL | Access |
|------|-----|--------|
| Login | http://localhost:3000/login.html | Public |
| Chat | http://localhost:3000/chat.html | Authenticated users |
| Manifest | http://localhost:3000/manifest.html | Admin only |

## 🔄 Complete Workflow

### 1. Upload Document (Regular User)
1. Login as `user@centef.org`
2. Go to Chat page
3. Drag & drop a PDF/DOCX in the sidebar OR click "Choose Files"
4. Document uploads → Status: `pending_processing`

### 2. Processing (Automatic)
- System processes the document into chunks
- Generates AI summary with Gemini
- Extracts metadata (author, date, tags, etc.)
- Status changes: `pending_processing` → `pending_summary` → `pending_approval`

### 3. Admin Review & Approval
1. Login as `admin@centef.org`
2. Go to Manifest page
3. Click "Pending Approvals" button
4. Click "Edit" on a document
5. Review/edit the extracted metadata
6. Click "✓ Approve & Index"
7. Status changes: `pending_approval` → `pending_embedding` → `embedded`

### 4. Query Documents (Any User)
1. Go to Chat page
2. Ask questions about the documents
3. Get AI-powered answers with source citations
4. Citations show which documents were used

## 📂 File Upload Support

| Type | Extensions | Notes |
|------|-----------|-------|
| PDF | `.pdf` | Standard text extraction |
| Word | `.docx`, `.doc` | Section-based chunking |
| Images | `.png`, `.jpg`, `.jpeg` | OCR with Vision API |
| Subtitles | `.srt` | Timestamp-based segments |

## 🛠️ Manual Startup (Alternative)

If the script doesn't work, start manually:

### Terminal 1 - Backend
```powershell
cd centef-rag-two-tier\apps\agent_api
conda activate ..\..\..\.conda
python main.py
```

### Terminal 2 - Frontend
```powershell
cd centef-rag-two-tier\apps\frontend
conda activate ..\..\..\.conda
python serve.py
```

### Terminal 3 - Open Browser
```powershell
start http://localhost:3000/login.html
```

## 🔍 Verify Setup

### Check Backend Health
```powershell
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

### Check Users Exist
```powershell
cd centef-rag-two-tier
python shared\user_management.py list
# Should show: admin@centef.org and user@centef.org
```

### Check Environment
```powershell
cd centef-rag-two-tier
python check_env.py
# Should show all required environment variables
```

## ❓ Troubleshooting

### Port Already in Use
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace <PID> with actual number)
taskkill /PID <PID> /F
```

### Backend Won't Start
1. Check conda environment: `conda activate .conda`
2. Check Python version: `python --version` (should be 3.10+)
3. Check dependencies: `pip list | findstr fastapi`
4. Check logs in terminal for specific errors

### Login Fails
1. Verify users exist: `python shared\user_management.py list`
2. Try creating a new user: `python shared\user_management.py add test@example.com TestPass123! "Test User"`
3. Check browser console (F12) for error details
4. Verify JWT_SECRET_KEY in `.env`

### Upload Fails
1. Check GCS authentication: `gcloud auth application-default login`
2. Verify SOURCE_BUCKET in `.env`: `echo $env:SOURCE_BUCKET`
3. Check file size (< 10 MB recommended)
4. Check file type is supported

### No Search Results
1. Verify documents are indexed:
   ```powershell
   python list_chunks.py
   python list_summaries.py
   ```
2. Check manifest status: should be `embedded`
3. Try reindexing: `python services\embedding\index_documents.py <source_id>`

## 🎯 Next Steps

1. **Customize branding:** Edit `apps\frontend\css\style.css`
2. **Add more users:** `python shared\user_management.py add <email> <password> "<name>"`
3. **Upload test documents:** Use the chat interface sidebar
4. **Monitor processing:** Check manifest page for document status
5. **Query the system:** Ask questions in chat interface

## 📚 Documentation

- **Full Frontend Guide:** `apps\frontend\README.md`
- **Admin Guide:** `ADMIN_GUIDE.md`
- **Chat Features:** `CHAT_HISTORY.md`
- **User Management:** `USER_MANAGEMENT.md`
- **API Instructions:** `.github\copilot-instructions.md`

## 🔐 Security Notes

⚠️ **This is a development setup. For production:**

1. Change default passwords immediately
2. Generate secure JWT secret: `openssl rand -hex 32`
3. Restrict CORS origins in `apps\agent_api\main.py`
4. Enable HTTPS/TLS
5. Use bcrypt for password hashing (not SHA-256)
6. Add rate limiting on authentication endpoints
7. Set up proper firewall rules

## 📞 Support

If you encounter issues:
1. Check browser console (F12 → Console tab)
2. Check backend logs in terminal
3. Review error messages carefully
4. Verify environment variables with `check_env.py`
