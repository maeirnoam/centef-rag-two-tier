# YouTube Downloader Service - External Deployment

This service runs on a non-cloud IP address (hstgr) to bypass YouTube's bot detection of Cloud Run IPs.

## Architecture

```
Cloud Run (FastAPI) → HTTP Request → External Server (hstgr) → pytubefix download → Return WAV file → Cloud Run uploads to GCS
```

## Setup on External Server (hstgr)

### 1. Install Dependencies

```bash
# Install Python 3.11+
sudo apt-get update
sudo apt-get install python3.11 python3-pip ffmpeg

# Install Python packages
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
# Generate a strong API key
export YOUTUBE_DOWNLOADER_API_KEY="your-strong-random-key-here"

# Or create .env file
echo "YOUTUBE_DOWNLOADER_API_KEY=your-strong-random-key-here" > .env
```

### 3. Run the Service

**Option A: Direct Python**
```bash
python main.py
```

**Option B: With systemd (recommended for production)**

Create `/etc/systemd/system/youtube-downloader.service`:
```ini
[Unit]
Description=YouTube Downloader Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/youtube-downloader
Environment="YOUTUBE_DOWNLOADER_API_KEY=your-key-here"
Environment="PORT=8080"
ExecStart=/usr/bin/python3 /opt/youtube-downloader/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable youtube-downloader
sudo systemctl start youtube-downloader
sudo systemctl status youtube-downloader
```

**Option C: With Docker**
```bash
docker build -t youtube-downloader .
docker run -d -p 8080:8080 \
  -e YOUTUBE_DOWNLOADER_API_KEY=your-key-here \
  --name youtube-downloader \
  youtube-downloader
```

### 4. Configure Reverse Proxy (Optional but Recommended)

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name youtube-dl.yourdomain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Important: Allow large file uploads/downloads
        client_max_body_size 500M;
        proxy_read_timeout 300s;
    }
}
```

For HTTPS (recommended):
```bash
sudo certbot --nginx -d youtube-dl.yourdomain.com
```

## Cloud Run Configuration

Set environment variable in Cloud Run:
```bash
YOUTUBE_DOWNLOADER_URL=https://youtube-dl.yourdomain.com
YOUTUBE_DOWNLOADER_API_KEY=your-key-here
```

## API Endpoints

### Health Check
```bash
GET /
GET /health
```

### Download Audio (Metadata Only)
```bash
POST /download
Headers:
  X-API-Key: your-api-key
Body:
  {
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "video_id": "VIDEO_ID"
  }
```

### Download Audio (File)
```bash
POST /download/file
Headers:
  X-API-Key: your-api-key
Body:
  {
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "video_id": "VIDEO_ID"
  }
Returns: audio/wav file
```

## Testing

```bash
# Test health check
curl http://localhost:8080/health

# Test download (replace with your API key)
curl -X POST http://localhost:8080/download/file \
  -H "X-API-Key: your-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    "video_id": "jNQXAC9IVRw"
  }' \
  --output test.wav
```

## Security Notes

1. **API Key**: Use a strong random key (32+ characters)
2. **Firewall**: Only allow connections from Cloud Run IP ranges
3. **HTTPS**: Use SSL/TLS in production
4. **Rate Limiting**: Consider adding rate limiting for abuse prevention
5. **Monitoring**: Set up logging and monitoring for failed requests

## Troubleshooting

**pytubefix fails:**
- Update pytubefix: `pip install --upgrade pytubefix`
- Check if YouTube changed their API

**ffmpeg not found:**
- Install: `sudo apt-get install ffmpeg`
- Check path: `which ffmpeg`

**Large file timeouts:**
- Increase nginx proxy_read_timeout
- Increase Cloud Run request timeout
- Check network bandwidth

## Performance

- Download speed: Depends on YouTube and your server bandwidth
- Typical 5-minute video: 30-60 seconds download + conversion
- Concurrent requests: Up to ~10 parallel downloads (adjust based on server resources)
