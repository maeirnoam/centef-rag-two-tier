# Local Testing Guide - External YouTube Downloader

Quick guide to test the external YouTube downloader service on your localhost before deploying to hstgr.

## Prerequisites

- ✅ Python 3.11+ installed
- ✅ ffmpeg installed (or run: `choco install ffmpeg`)

## Step 1: Start the External Service (1 minute)

Open a **new PowerShell terminal** and run:

```powershell
.\apps\youtube_downloader\start-local.ps1
```

You should see:
```
========================================
YouTube Downloader Service - Local Test
========================================
...
Configuration:
  URL: http://127.0.0.1:8080
  API Key: local-test-key-12345
========================================

Starting service...
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8080
```

**Keep this terminal open!** The service needs to keep running.

## Step 2: Test the Service (1 minute)

In another PowerShell terminal:

```powershell
.\apps\youtube_downloader\test-local.ps1
```

You should see:
```
========================================
Testing YouTube Downloader (Localhost)
========================================

[1/3] Testing health endpoint...
✓ Health check passed

[2/3] Testing download endpoint (metadata)...
✓ Metadata download successful

[3/3] Testing file download...
✓ File download successful
  Size: 10.99 MB
```

## Step 3: Configure Backend to Use Local Service (30 seconds)

Edit `.env` file and uncomment these lines:

```env
YOUTUBE_DOWNLOADER_URL=http://127.0.0.1:8080
YOUTUBE_DOWNLOADER_API_KEY=local-test-key-12345
```

## Step 4: Start Local Backend (1 minute)

In another PowerShell terminal:

```powershell
.\start-local.ps1
```

## Step 5: Test End-to-End (2 minutes)

1. Open browser: http://localhost:8080
2. Login with admin credentials
3. Go to "Contribute" page
4. Enter a YouTube URL
5. Click "Upload YouTube Video"
6. Check the backend terminal - you should see:
   ```
   Using external YouTube downloader service (non-cloud IP)...
   ✓ External download successful
   ```

## Troubleshooting

### ffmpeg not found

```powershell
# Install with chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

### Port 8080 already in use

```powershell
# Find what's using port 8080
netstat -ano | findstr :8080

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F

# Or change the port in start-local.ps1
```

### pytubefix fails

```powershell
# Update pytubefix
cd apps\youtube_downloader
.\venv\Scripts\Activate.ps1
pip install --upgrade pytubefix
```

### Connection refused

Make sure:
1. External service is running (check terminal)
2. Backend .env has correct URL: `http://127.0.0.1:8080`
3. API key matches: `local-test-key-12345`

## Architecture

```
┌─────────────────────────┐
│   Browser               │
│   localhost:8080        │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Backend (FastAPI)     │
│   localhost:8080        │
└───────────┬─────────────┘
            │ HTTP Request
            ▼
┌─────────────────────────┐
│   YouTube Downloader    │
│   127.0.0.1:8080        │
│   (External Service)    │
└───────────┬─────────────┘
            │ pytubefix
            ▼
┌─────────────────────────┐
│   YouTube               │
└─────────────────────────┘
```

## What's Different from Production?

| Aspect | Local Testing | Production (hstgr) |
|--------|--------------|-------------------|
| URL | `http://127.0.0.1:8080` | `https://youtube-dl.yourdomain.com` |
| API Key | `local-test-key-12345` | Strong random key |
| HTTPS | No | Yes (Let's Encrypt) |
| systemd | No | Yes |
| Nginx | No | Yes |
| Startup | Manual | Automatic |

## Next Steps

Once local testing works:

1. **Deploy to hstgr**: Follow `apps/youtube_downloader/DEPLOYMENT.md`
2. **Update .env**: Change URL to your hstgr domain
3. **Deploy to Cloud Run**: Run `.\deploy-backend-simple.ps1`

## Stopping Services

**External Service**: Press `Ctrl+C` in the terminal

**Backend**: Press `Ctrl+C` in the terminal

**Clean up**: Comment out the external downloader config in `.env` to go back to local downloads

## Performance

Local testing should show similar performance to production:
- Short video (5 min): ~30-60 seconds
- Download happens on localhost (fast)
- No network latency between services

## Done!

You now have a local testing environment for the external YouTube downloader! 🎉

When everything works locally, deploy to hstgr for production use.
