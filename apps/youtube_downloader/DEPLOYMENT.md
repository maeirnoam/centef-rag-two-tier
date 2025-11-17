# YouTube Downloader Service - Deployment to hstgr

Complete guide to deploy the external YouTube downloader service on your hstgr server.

## Prerequisites

- Server with Ubuntu 20.04+ or similar Linux distribution
- Python 3.11 or higher
- ffmpeg
- sudo/root access
- Domain name (optional but recommended for HTTPS)

## Step 1: Prepare Server

### 1.1 SSH into your hstgr server

```bash
ssh your-user@your-hstgr-server.com
```

### 1.2 Install required packages

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv ffmpeg nginx
```

### 1.3 Verify installations

```bash
python3 --version  # Should be 3.11+
ffmpeg -version
```

## Step 2: Deploy Service Files

### 2.1 Create service directory

```bash
sudo mkdir -p /opt/youtube-downloader
sudo chown $USER:$USER /opt/youtube-downloader
```

### 2.2 Copy files to server

From your local machine:

```bash
# Copy service files
scp apps/youtube_downloader/main.py your-user@your-server:/opt/youtube-downloader/
scp apps/youtube_downloader/requirements.txt your-user@your-server:/opt/youtube-downloader/
scp apps/youtube_downloader/start.sh your-user@your-server:/opt/youtube-downloader/
scp apps/youtube_downloader/stop.sh your-user@your-server:/opt/youtube-downloader/
scp apps/youtube_downloader/youtube-downloader.service your-user@your-server:/tmp/

# Or use rsync
rsync -avz apps/youtube_downloader/ your-user@your-server:/opt/youtube-downloader/
```

### 2.3 Set permissions

```bash
cd /opt/youtube-downloader
chmod +x start.sh stop.sh
```

## Step 3: Generate Strong API Key

```bash
# Generate a random 32-character key
openssl rand -hex 32
# Example output: a1b2c3d4e5f6...
```

**Save this key!** You'll need it for both the external service and Cloud Run.

## Step 4: Configure systemd Service

### 4.1 Edit service file with your API key

```bash
sudo nano /tmp/youtube-downloader.service
```

Replace `CHANGE_ME_TO_STRONG_RANDOM_KEY` with your generated API key.

### 4.2 Install service file

```bash
sudo cp /tmp/youtube-downloader.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 4.3 Create log directory

```bash
sudo mkdir -p /var/log/youtube-downloader
sudo chown www-data:www-data /var/log/youtube-downloader
```

## Step 5: Setup Python Environment

```bash
cd /opt/youtube-downloader

# Create virtual environment
python3 -m venv venv

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

## Step 6: Configure Nginx (Reverse Proxy)

### 6.1 Create Nginx configuration

```bash
sudo nano /etc/nginx/sites-available/youtube-downloader
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name youtube-dl.yourdomain.com;  # Change to your domain or IP

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Important for large file downloads
        client_max_body_size 500M;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

### 6.2 Enable site

```bash
sudo ln -s /etc/nginx/sites-available/youtube-downloader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6.3 Configure firewall

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
```

## Step 7: Setup HTTPS with Let's Encrypt (Recommended)

### 7.1 Install Certbot

```bash
sudo apt-get install -y certbot python3-certbot-nginx
```

### 7.2 Get SSL certificate

```bash
sudo certbot --nginx -d youtube-dl.yourdomain.com
```

Follow the prompts. Certbot will automatically configure HTTPS.

## Step 8: Start Service

### 8.1 Enable and start

```bash
sudo systemctl enable youtube-downloader
sudo systemctl start youtube-downloader
```

### 8.2 Check status

```bash
sudo systemctl status youtube-downloader
```

Should show "active (running)".

### 8.3 View logs

```bash
sudo journalctl -u youtube-downloader -f
# Or
tail -f /var/log/youtube-downloader/output.log
```

## Step 9: Test Service

### 9.1 Health check

```bash
curl http://localhost:8080/health
```

Should return:
```json
{
  "status": "healthy",
  "pytubefix": "available",
  "ffmpeg": "available"
}
```

### 9.2 Test download

```bash
curl -X POST http://localhost:8080/download/file \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    "video_id": "test123"
  }' \
  --output test.wav
```

Check file was created:
```bash
ls -lh test.wav
file test.wav  # Should say "RIFF (little-endian) data, WAVE audio"
```

## Step 10: Configure Cloud Run

### 10.1 Add to .env file

```bash
YOUTUBE_DOWNLOADER_URL=https://youtube-dl.yourdomain.com
YOUTUBE_DOWNLOADER_API_KEY=YOUR_API_KEY_HERE
YOUTUBE_DOWNLOADER_TIMEOUT=300
```

### 10.2 Deploy backend

```powershell
.\deploy-backend-simple.ps1
```

### 10.3 Test from Cloud Run

Check health endpoint:
```bash
curl https://your-cloud-run-url.run.app/health
```

Should include:
```json
{
  "status": "healthy",
  "external_youtube_downloader": {
    "configured": true,
    "status": "healthy",
    "url": "https://youtube-dl.yourdomain.com"
  }
}
```

## Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u youtube-downloader -n 50
sudo tail -f /var/log/youtube-downloader/error.log

# Check if port is already in use
sudo netstat -tulpn | grep 8080

# Test Python directly
cd /opt/youtube-downloader
source venv/bin/activate
python main.py
```

### Download fails

```bash
# Check ffmpeg
which ffmpeg
ffmpeg -version

# Check Python packages
source /opt/youtube-downloader/venv/bin/activate
pip list | grep pytubefix

# Update pytubefix
pip install --upgrade pytubefix
```

### Nginx errors

```bash
# Check Nginx config
sudo nginx -t

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log

# Restart Nginx
sudo systemctl restart nginx
```

### Cloud Run can't connect

1. Check firewall allows incoming connections
2. Verify domain DNS is correct
3. Test from another server: `curl -I https://youtube-dl.yourdomain.com/health`
4. Check API key matches in both places

## Maintenance

### Update service

```bash
# Stop service
sudo systemctl stop youtube-downloader

# Update files
cd /opt/youtube-downloader
# Copy new files here

# Update dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt
deactivate

# Start service
sudo systemctl start youtube-downloader
```

### View resource usage

```bash
# CPU and memory
htop
# Or
ps aux | grep python

# Disk usage
df -h
du -sh /opt/youtube-downloader
```

### Rotate logs

Create `/etc/logrotate.d/youtube-downloader`:
```
/var/log/youtube-downloader/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload youtube-downloader > /dev/null 2>&1 || true
    endscript
}
```

## Security Hardening

### Restrict API access to Cloud Run IPs only

Get Cloud Run IP ranges:
```bash
# Cloud Run uses Google Cloud IP ranges
# Download from: https://www.gstatic.com/ipranges/cloud.json
```

Configure firewall:
```bash
# Example for specific IP
sudo ufw allow from 35.190.0.0/16 to any port 80
sudo ufw allow from 35.190.0.0/16 to any port 443
```

### Fail2ban for rate limiting

```bash
sudo apt-get install fail2ban

# Configure in /etc/fail2ban/jail.local
```

### Monitor service

Setup monitoring with:
- Prometheus
- Grafana
- Uptime monitoring service

## Cost Optimization

- Use smallest server instance that handles your load
- Monitor bandwidth usage (YouTube downloads can be large)
- Consider rate limiting requests from Cloud Run
- Cache popular videos (optional advanced feature)

## Done!

Your external YouTube downloader service should now be running and accessible from Cloud Run. 🎉
