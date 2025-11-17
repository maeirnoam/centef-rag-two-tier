# Quick Start: External YouTube Downloader

Get the external YouTube downloader service running in 10 minutes.

## Prerequisites
- Server with Ubuntu/Debian
- Python 3.11+
- sudo access

## 1. Generate API Key (30 seconds)

```bash
openssl rand -hex 32
```

Copy this key - you'll need it twice.

## 2. Deploy to External Server (5 minutes)

```bash
# SSH to your server
ssh user@your-hstgr-server.com

# Install dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv ffmpeg

# Create directory
sudo mkdir -p /opt/youtube-downloader
sudo chown $USER:$USER /opt/youtube-downloader
cd /opt/youtube-downloader
```

Copy these 2 files from your local machine:
```bash
# On your local machine
scp apps/youtube_downloader/main.py user@your-server:/opt/youtube-downloader/
scp apps/youtube_downloader/requirements.txt user@your-server:/opt/youtube-downloader/
```

Back on the server:
```bash
# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set API key and run
export YOUTUBE_DOWNLOADER_API_KEY="YOUR_KEY_HERE"
python main.py
```

Service should start on port 8080.

## 3. Test It (1 minute)

In another terminal on the server:
```bash
curl http://localhost:8080/health
```

Should return:
```json
{"status":"healthy","pytubefix":"available"}
```

## 4. Configure Cloud Run (2 minutes)

In your `.env` file:
```env
YOUTUBE_DOWNLOADER_URL=http://your-server-ip:8080
YOUTUBE_DOWNLOADER_API_KEY=YOUR_KEY_HERE
```

Deploy backend:
```powershell
.\deploy-backend-simple.ps1
```

## 5. Test End-to-End (2 minutes)

```bash
# Check Cloud Run health
curl https://your-cloud-run-url.run.app/health
```

Should show:
```json
{
  "status": "healthy",
  "external_youtube_downloader": {
    "configured": true,
    "status": "healthy"
  }
}
```

Try uploading a YouTube video via the frontend!

## Production Setup

For production, you should:

1. **Setup systemd** (so service starts on boot)
2. **Add Nginx reverse proxy** (for HTTPS)
3. **Get SSL certificate** (with Let's Encrypt)
4. **Use domain name** (instead of IP)

See [DEPLOYMENT.md](apps/youtube_downloader/DEPLOYMENT.md) for full production setup.

## Troubleshooting

**Service won't start:**
```bash
# Check Python version
python3 --version  # Need 3.11+

# Check ffmpeg
ffmpeg -version

# Run directly to see errors
cd /opt/youtube-downloader
source venv/bin/activate
python main.py
```

**Cloud Run can't connect:**
- Check firewall allows connections
- Verify URL is correct in .env
- Test from your machine: `curl http://your-server-ip:8080/health`

**Downloads fail:**
```bash
# Update pytubefix
source /opt/youtube-downloader/venv/bin/activate
pip install --upgrade pytubefix
```

## Done! 🎉

Your external YouTube downloader is now handling downloads from a non-cloud IP, bypassing YouTube's bot detection!
