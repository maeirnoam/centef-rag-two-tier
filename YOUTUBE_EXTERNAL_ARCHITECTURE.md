# External YouTube Downloader Architecture

## Overview

This architecture solves YouTube's bot detection of Cloud Run IP addresses by offloading video downloads to an external server (hstgr) with a non-cloud IP address.

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Action                                  │
│            (Upload YouTube URL via Frontend)                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Cloud Run (FastAPI Backend)                       │
│  • Receives YouTube URL                                              │
│  • Creates manifest entry                                            │
│  • Triggers background task: process_youtube_video()                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
          ┌────────────────────────────────────┐
          │  Is External Service Configured?   │
          └────────┬───────────────────┬───────┘
                   │ YES               │ NO
                   ▼                   ▼
    ┌──────────────────────┐   ┌─────────────────────┐
    │ External Downloader  │   │ Local Download      │
    │ (Preferred)          │   │ (Fallback)          │
    └──────┬───────────────┘   └──────┬──────────────┘
           │                          │
           ▼                          ▼
┌─────────────────────────┐   ┌──────────────────────┐
│  POST /download/file    │   │ pytubefix → yt-dlp   │
│  to hstgr server        │   │ (May be blocked)     │
└─────────┬───────────────┘   └──────┬───────────────┘
          │                          │
          ▼                          │
┌─────────────────────────┐          │
│ External Server (hstgr) │          │
│  • Non-cloud IP         │          │
│  • Downloads with       │          │
│    pytubefix            │          │
│  • Converts to WAV      │          │
│  • Returns file         │          │
└─────────┬───────────────┘          │
          │                          │
          └──────────┬───────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  WAV Audio File      │
          │  (16kHz mono)        │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Upload to GCS       │
          │  gs://bucket/data/   │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Speech-to-Text API  │
          │  (Transcription)     │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Translation API     │
          │  (if needed)         │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Chunking            │
          │  (30s windows)       │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Summarization       │
          │  (Gemini)            │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  PENDING_APPROVAL    │
          │  (Admin review)      │
          └──────────────────────┘
```

## Components

### 1. External YouTube Downloader Service

**Location**: `apps/youtube_downloader/`

**Files**:
- `main.py` - FastAPI service
- `requirements.txt` - Minimal dependencies (no GCS)
- `Dockerfile` - Container for deployment
- `README.md` - Service documentation
- `DEPLOYMENT.md` - Deployment guide for hstgr
- `start.sh` / `stop.sh` - Service management scripts
- `youtube-downloader.service` - systemd configuration

**Key Features**:
- Lightweight FastAPI service
- Only dependencies: `fastapi`, `uvicorn`, `pytubefix`, `ffmpeg`
- No GCS credentials needed (more secure)
- API key authentication
- Returns WAV files via HTTP

**Endpoints**:
- `GET /` - Root health check
- `GET /health` - Detailed health status
- `POST /download` - Download metadata only
- `POST /download/file` - Download and return WAV file

### 2. Cloud Run Client

**Location**: `tools/processing/youtube_downloader_client.py`

**Functions**:
- `is_external_downloader_configured()` - Check if service is set up
- `download_youtube_via_external_service()` - Download via HTTP
- `health_check_external_service()` - Verify service availability

**Configuration** (Environment Variables):
- `YOUTUBE_DOWNLOADER_URL` - External service URL
- `YOUTUBE_DOWNLOADER_API_KEY` - API key for authentication
- `YOUTUBE_DOWNLOADER_TIMEOUT` - Request timeout (default 300s)

### 3. Modified Cloud Run Backend

**File**: `apps/agent_api/main.py`

**Changes**:
- `process_youtube_video()` now tries external service first
- Falls back to local download if external service fails
- Health endpoint includes external service status

## Security

### Authentication
- API key in HTTP header: `X-API-Key`
- Generated using: `openssl rand -hex 32`
- Stored in environment variables (not in code)

### Network Security
- HTTPS recommended (Let's Encrypt)
- Optional: Restrict to Cloud Run IP ranges via firewall
- Optional: VPN tunnel between Cloud Run and hstgr

### Data Security
- **No GCS credentials on external server**
- Files transferred over HTTPS
- Temporary files cleaned up automatically
- No persistent storage on external server

## Deployment

### External Service (hstgr)

1. **Install Dependencies**:
   ```bash
   sudo apt-get install python3 python3-pip ffmpeg nginx
   ```

2. **Deploy Service**:
   ```bash
   # Copy files
   rsync -avz apps/youtube_downloader/ user@hstgr:/opt/youtube-downloader/
   
   # Setup
   cd /opt/youtube-downloader
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure systemd**:
   ```bash
   sudo cp youtube-downloader.service /etc/systemd/system/
   sudo systemctl enable youtube-downloader
   sudo systemctl start youtube-downloader
   ```

4. **Setup Nginx + HTTPS**:
   ```bash
   sudo certbot --nginx -d youtube-dl.yourdomain.com
   ```

### Cloud Run Backend

1. **Update .env**:
   ```env
   YOUTUBE_DOWNLOADER_URL=https://youtube-dl.yourdomain.com
   YOUTUBE_DOWNLOADER_API_KEY=your-generated-key
   YOUTUBE_DOWNLOADER_TIMEOUT=300
   ```

2. **Deploy**:
   ```powershell
   .\deploy-backend-simple.ps1
   ```

## Testing

### Test External Service

```bash
# Health check
curl https://youtube-dl.yourdomain.com/health

# Test download
curl -X POST https://youtube-dl.yourdomain.com/download/file \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID", "video_id": "VIDEO_ID"}' \
  --output test.wav
```

### Test Integration

```bash
# From Cloud Run backend
python test_external_youtube_downloader.py
```

### Test End-to-End

1. Open frontend: `https://your-frontend.run.app`
2. Go to "Contribute" page
3. Enter YouTube URL
4. Submit
5. Check Cloud Run logs: Should show "Using external YouTube downloader service"
6. Verify file appears in GCS
7. Check manifest status: Should progress to PENDING_APPROVAL

## Monitoring

### External Service Logs

```bash
# systemd logs
sudo journalctl -u youtube-downloader -f

# File logs
tail -f /var/log/youtube-downloader/output.log
```

### Cloud Run Logs

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=centef-rag-api" --limit 50
```

### Health Checks

```bash
# External service
curl https://youtube-dl.yourdomain.com/health

# Cloud Run (includes external service status)
curl https://your-cloud-run.run.app/health
```

## Troubleshooting

### External Service Not Responding

1. Check service status: `sudo systemctl status youtube-downloader`
2. Check logs: `sudo journalctl -u youtube-downloader -n 100`
3. Test locally: `curl http://localhost:8080/health`
4. Check nginx: `sudo nginx -t && sudo systemctl status nginx`
5. Check firewall: `sudo ufw status`

### Downloads Failing

1. Check pytubefix version: `pip list | grep pytubefix`
2. Update if needed: `pip install --upgrade pytubefix`
3. Test ffmpeg: `ffmpeg -version`
4. Check disk space: `df -h`
5. Check temp directory permissions: `ls -ld /tmp`

### Cloud Run Can't Connect

1. Verify URL in .env
2. Check API key matches
3. Test from another location: `curl https://youtube-dl.yourdomain.com/health`
4. Check DNS: `nslookup youtube-dl.yourdomain.com`
5. Check SSL certificate: `curl -I https://youtube-dl.yourdomain.com`

## Performance

### Typical Performance
- Short video (5 min): ~30-60 seconds
- Medium video (15 min): ~1-2 minutes
- Long video (60 min): ~5-10 minutes

### Bottlenecks
1. **YouTube download speed** - Limited by YouTube and network
2. **File transfer** - Limited by bandwidth between hstgr and Cloud Run
3. **ffmpeg conversion** - CPU-bound, usually fast

### Optimization
- Use a server with good network connectivity
- Consider caching popular videos (advanced)
- Scale horizontally by adding more external servers (load balancer)

## Cost Analysis

### External Server (hstgr)
- Server: ~$5-20/month (depending on specs)
- Bandwidth: Variable (watch for overages)
- Domain + SSL: Free (Let's Encrypt)

### Cloud Run
- No change to existing costs
- May reduce request failures (fewer retries)

### ROI
- ✅ Bypasses YouTube bot detection
- ✅ More reliable downloads
- ✅ Better user experience
- ✅ Keeps GCS credentials secure

## Alternatives Considered

1. **Local download from Cloud Run**
   - ❌ YouTube blocks cloud IPs
   - Tried: pytubefix, yt-dlp, cookies, randomization
   - Result: Still blocked

2. **External service with GCS credentials**
   - ✅ Faster (direct upload)
   - ❌ Less secure (credentials on external server)
   - Rejected for security reasons

3. **YouTube Data API**
   - ❌ No audio download capability
   - ❌ Limited quota
   - Only useful for metadata

4. **Third-party services (YT-DL servers)**
   - ❌ Privacy concerns
   - ❌ Reliability
   - ❌ Cost

## Future Enhancements

1. **Load Balancing**: Multiple external servers
2. **Caching**: Store popular videos
3. **Queue Management**: Handle concurrent requests
4. **Metrics**: Track download success/failure rates
5. **Auto-scaling**: Scale external servers based on demand
6. **Webhook**: Async notification instead of blocking
7. **Resume Downloads**: Handle interrupted transfers
8. **Format Selection**: Allow quality/format preferences

## Conclusion

This architecture provides a **secure, scalable, and reliable** solution for YouTube video ingestion by:
- Bypassing Cloud Run IP detection
- Keeping GCS credentials secure
- Providing graceful fallback mechanisms
- Maintaining audit trails and logs
- Being cost-effective and maintainable

The trade-off (slower file transfer vs. more reliable downloads) is acceptable given the previous 100% failure rate from Cloud Run.
