# YouTube Downloader to Hostinger VPS - Deployment Summary

## 📦 What You're Deploying

A lightweight YouTube downloader service that runs on your Hostinger VPS to bypass YouTube's bot detection of Cloud Run IP addresses.

**Service Details:**
- **Language:** Python 3.8+
- **Framework:** FastAPI
- **Dependencies:** pytubefix, uvicorn, ffmpeg
- **Port:** 8080 (internal), 80 (via Nginx)
- **Authentication:** API Key

## 🔑 Generated Credentials

**API Key:**
```
540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55
```

**Important:** Keep this key secure. It will be used by:
1. Hostinger VPS service (to validate requests)
2. Cloud Run backend (to authenticate with VPS)

## 📁 Files Created

I've created the following deployment resources:

1. **[HOSTINGER_DEPLOYMENT_GUIDE.md](HOSTINGER_DEPLOYMENT_GUIDE.md)**
   - Complete step-by-step deployment guide
   - Troubleshooting section
   - Security hardening tips

2. **[apps/youtube_downloader/QUICK_DEPLOY.md](apps/youtube_downloader/QUICK_DEPLOY.md)**
   - Quick reference checklist
   - Copy-paste friendly commands
   - Condensed version for experienced users

3. **[ENV_UPDATE_INSTRUCTIONS.md](ENV_UPDATE_INSTRUCTIONS.md)**
   - Instructions for updating .env file
   - Configuration examples

4. **[test_hostinger_youtube_downloader.py](test_hostinger_youtube_downloader.py)**
   - Test script to verify deployment
   - Checks connectivity, health, authentication, and downloads

## 🚀 Quick Start

### Phase 1: Deploy to Hostinger VPS

1. **Get VPS access:**
   - Go to https://hpanel.hostinger.com/vps/974700/overview
   - Get SSH credentials (IP, username, password)

2. **SSH into VPS:**
   ```bash
   ssh root@YOUR_VPS_IP
   ```

3. **Follow the Quick Deploy Guide:**
   - Open [apps/youtube_downloader/QUICK_DEPLOY.md](apps/youtube_downloader/QUICK_DEPLOY.md)
   - Execute steps 1️⃣ through 7️⃣ on the VPS
   - Takes approximately 10-15 minutes

### Phase 2: Configure Cloud Run

4. **Update .env file:**
   ```env
   YOUTUBE_DOWNLOADER_URL=http://YOUR_VPS_IP
   YOUTUBE_DOWNLOADER_API_KEY=540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55
   YOUTUBE_DOWNLOADER_TIMEOUT=300
   ```

5. **Deploy Cloud Run:**
   ```powershell
   .\deploy-backend-simple.ps1
   ```

### Phase 3: Test

6. **Test VPS service:**
   ```powershell
   python test_hostinger_youtube_downloader.py
   ```

7. **Test end-to-end:**
   - Go to your frontend
   - Upload a YouTube video
   - Monitor logs on both VPS and Cloud Run

## 📊 Architecture Overview

```
┌─────────────┐
│   Frontend  │
│  (Cloud Run)│
└──────┬──────┘
       │ Upload YouTube URL
       ▼
┌─────────────────────┐
│  Cloud Run Backend  │
│  - Creates manifest │
│  - Calls external   │
│    downloader       │
└──────┬──────────────┘
       │ HTTP Request (with API Key)
       ▼
┌───────────────────────┐
│  Hostinger VPS        │
│  ┌─────────────────┐  │
│  │ YouTube Service │  │
│  │ (FastAPI)       │  │
│  │ Port: 8080      │  │
│  └────────┬────────┘  │
│           │           │
│  ┌────────▼────────┐  │
│  │ Nginx           │  │
│  │ (Reverse Proxy) │  │
│  │ Port: 80        │  │
│  └─────────────────┘  │
└───────────────────────┘
       │ Downloads from YouTube
       ▼
┌─────────────────┐
│    YouTube      │
└─────────────────┘
```

**Why this works:**
- Hostinger VPS has a residential/datacenter IP (not Cloud IP)
- YouTube doesn't block these IPs
- Cloud Run securely fetches the downloaded file

## 🔐 Security Features

1. **API Key Authentication:** All requests require valid API key
2. **No GCS credentials on VPS:** More secure, VPS only downloads
3. **File transfer over HTTP:** Can upgrade to HTTPS with Let's Encrypt
4. **Temporary file cleanup:** Files deleted after transfer
5. **Firewall protection:** Only expose necessary ports

## 📈 What Happens When You Upload a YouTube Video

1. **User submits YouTube URL** via frontend
2. **Cloud Run creates manifest entry** (status: PROCESSING)
3. **Cloud Run calls Hostinger VPS** with API key
4. **VPS downloads audio** using pytubefix (bypasses bot detection)
5. **VPS converts to WAV** using ffmpeg (16kHz mono)
6. **VPS streams file back** to Cloud Run via HTTP
7. **Cloud Run uploads to GCS** (Google Cloud Storage)
8. **Cloud Run transcribes** using Speech-to-Text API
9. **Cloud Run translates** (if needed)
10. **Cloud Run chunks** into 30-second segments
11. **Cloud Run summarizes** using Gemini
12. **Status updates to PENDING_APPROVAL** for admin review

## 🧪 Testing Checklist

- [ ] VPS service is running: `sudo systemctl status youtube-downloader`
- [ ] VPS responds to health check: `curl http://VPS_IP/health`
- [ ] Nginx is configured and running
- [ ] Firewall allows port 80
- [ ] Test script passes all tests
- [ ] Cloud Run can reach VPS
- [ ] End-to-end test via frontend works
- [ ] Check logs on both VPS and Cloud Run
- [ ] Verify file appears in GCS
- [ ] Confirm manifest status updates

## 📝 Important Files Locations

**On Hostinger VPS:**
- Service code: `/opt/youtube-downloader/main.py`
- Service config: `/etc/systemd/system/youtube-downloader.service`
- Nginx config: `/etc/nginx/sites-available/youtube-downloader`
- Logs: `/var/log/youtube-downloader/`

**On Your Local Machine:**
- Main service: `apps/youtube_downloader/main.py`
- Requirements: `apps/youtube_downloader/requirements.txt`
- Environment: `.env` (update with VPS IP)
- Test script: `test_hostinger_youtube_downloader.py`

## 🔧 Useful Commands

**On VPS:**
```bash
# Service management
sudo systemctl status youtube-downloader
sudo systemctl restart youtube-downloader
sudo systemctl stop youtube-downloader

# View logs
sudo journalctl -u youtube-downloader -f
tail -f /var/log/youtube-downloader/output.log

# Test locally
curl http://localhost:8080/health

# Check processes
ps aux | grep python
```

**On Local Machine:**
```powershell
# Test VPS connection
python test_hostinger_youtube_downloader.py

# Deploy Cloud Run
.\deploy-backend-simple.ps1

# Check Cloud Run logs
gcloud logging tail "resource.type=cloud_run_revision" --limit 50
```

## 🆘 Troubleshooting

### Service won't start on VPS
```bash
sudo journalctl -u youtube-downloader -n 50
# Check for Python errors, missing dependencies, or port conflicts
```

### Cloud Run can't connect to VPS
1. Check firewall: `sudo ufw status`
2. Test from outside: `curl http://VPS_IP/health`
3. Verify API key matches in .env and VPS config

### Downloads fail
```bash
# Update pytubefix
cd /opt/youtube-downloader
source venv/bin/activate
pip install --upgrade pytubefix
```

### Large files timeout
- Increase `YOUTUBE_DOWNLOADER_TIMEOUT` in .env (default: 300s)
- Check VPS bandwidth/network speed

## 🎯 Next Steps After Deployment

1. **Monitor Performance:**
   - Track download success rate
   - Monitor VPS resource usage (CPU, RAM, disk)
   - Watch for YouTube API changes

2. **Optional Enhancements:**
   - Setup HTTPS with Let's Encrypt
   - Add monitoring/alerting (Prometheus, Grafana)
   - Implement rate limiting
   - Setup log rotation

3. **Production Readiness:**
   - Backup VPS configuration
   - Document any custom changes
   - Setup automated health checks
   - Consider failover options

## 📚 Documentation References

- **Full Guide:** [HOSTINGER_DEPLOYMENT_GUIDE.md](HOSTINGER_DEPLOYMENT_GUIDE.md)
- **Quick Reference:** [apps/youtube_downloader/QUICK_DEPLOY.md](apps/youtube_downloader/QUICK_DEPLOY.md)
- **Architecture:** [YOUTUBE_EXTERNAL_ARCHITECTURE.md](YOUTUBE_EXTERNAL_ARCHITECTURE.md)
- **Service README:** [apps/youtube_downloader/README.md](apps/youtube_downloader/README.md)

## ✅ Success Criteria

Your deployment is successful when:

1. ✓ VPS service shows "active (running)"
2. ✓ Health endpoint returns `{"status":"healthy"}`
3. ✓ Test script passes all tests
4. ✓ Cloud Run health shows external_youtube_downloader as "healthy"
5. ✓ YouTube video upload works end-to-end
6. ✓ File appears in GCS after processing
7. ✓ Manifest status updates to PENDING_APPROVAL

## 🎉 You're Ready!

Everything is prepared for deployment. Follow the guides step-by-step, and you'll have your YouTube downloader running on Hostinger VPS in no time.

**Need help?** Check the troubleshooting sections in the guides or review the logs on both VPS and Cloud Run.

Good luck! 🚀
