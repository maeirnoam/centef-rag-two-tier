# YouTube Downloader Deployment to Hostinger VPS

## Overview
This guide walks you through deploying the YouTube downloader service to your Hostinger VPS.

## Generated Credentials

**API Key (SAVE THIS):**
```
540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55
```

You'll need this key for:
1. Configuring the service on Hostinger VPS
2. Configuring Cloud Run to connect to the service

---

## Prerequisites

### 1. Access Your Hostinger VPS

1. Go to https://hpanel.hostinger.com/vps/974700/overview
2. Find SSH access details:
   - Click on "SSH Access" or "Access Details"
   - Note your SSH credentials (IP, port, username, password or key)
3. Get VPS IP address from the overview page

### 2. SSH Into Your VPS

From your Windows machine, use PowerShell or Windows Terminal:

```powershell
ssh root@YOUR_VPS_IP
# Or if you have a specific user and port:
ssh -p PORT USERNAME@YOUR_VPS_IP
```

---

## Step-by-Step Deployment

### Step 1: Prepare the VPS (Run on VPS via SSH)

```bash
# Update system packages
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y python3 python3-pip python3-venv ffmpeg nginx

# Verify installations
python3 --version  # Should be 3.8+
ffmpeg -version    # Should show ffmpeg version
```

### Step 2: Create Service Directory

```bash
# Create service directory
sudo mkdir -p /opt/youtube-downloader
sudo chown $USER:$USER /opt/youtube-downloader
cd /opt/youtube-downloader
```

### Step 3: Upload Files to VPS

**Option A: Using SCP from Windows PowerShell**

Open a NEW PowerShell window on your local machine (not SSH session):

```powershell
# Navigate to your project
cd C:\Users\User\PycharmProjects\centef-rag-fresh

# Upload files (replace YOUR_VPS_IP and USERNAME)
scp apps\youtube_downloader\main.py USERNAME@YOUR_VPS_IP:/opt/youtube-downloader/
scp apps\youtube_downloader\requirements.txt USERNAME@YOUR_VPS_IP:/opt/youtube-downloader/
scp apps\youtube_downloader\start.sh USERNAME@YOUR_VPS_IP:/opt/youtube-downloader/
scp apps\youtube_downloader\stop.sh USERNAME@YOUR_VPS_IP:/opt/youtube-downloader/
scp apps\youtube_downloader\youtube-downloader.service USERNAME@YOUR_VPS_IP:/tmp/
```

**Option B: Using WinSCP or FileZilla**

1. Download WinSCP: https://winscp.net/
2. Connect to your VPS using the SSH credentials
3. Upload these files from `apps\youtube_downloader\` to `/opt/youtube-downloader/`:
   - main.py
   - requirements.txt
   - start.sh
   - stop.sh
4. Upload `youtube-downloader.service` to `/tmp/`

**Option C: Manual Copy-Paste (for small files)**

1. SSH into VPS
2. Create files manually:

```bash
cd /opt/youtube-downloader

# Create main.py
nano main.py
# Copy-paste content from apps/youtube_downloader/main.py
# Press Ctrl+X, then Y, then Enter to save

# Create requirements.txt
nano requirements.txt
# Copy-paste content from apps/youtube_downloader/requirements.txt
# Save with Ctrl+X, Y, Enter
```

### Step 4: Set Permissions

```bash
cd /opt/youtube-downloader
chmod +x start.sh stop.sh
```

### Step 5: Setup Python Environment

```bash
cd /opt/youtube-downloader

# Create virtual environment
python3 -m venv venv

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Verify installations
pip list | grep -E "fastapi|uvicorn|pytubefix"

# Deactivate for now
deactivate
```

### Step 6: Configure systemd Service

```bash
# Edit the service file to add your API key
sudo nano /tmp/youtube-downloader.service
```

Find this line:
```
Environment="YOUTUBE_DOWNLOADER_API_KEY=CHANGE_ME_TO_STRONG_RANDOM_KEY"
```

Replace with:
```
Environment="YOUTUBE_DOWNLOADER_API_KEY=540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55"
```

Save with `Ctrl+X`, `Y`, `Enter`

```bash
# Install service file
sudo cp /tmp/youtube-downloader.service /etc/systemd/system/
sudo systemctl daemon-reload

# Create log directory
sudo mkdir -p /var/log/youtube-downloader
sudo chown www-data:www-data /var/log/youtube-downloader
```

### Step 7: Configure Nginx (Reverse Proxy)

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/youtube-downloader
```

Paste this configuration (replace YOUR_VPS_IP with actual IP):

```nginx
server {
    listen 80;
    server_name YOUR_VPS_IP;  # Or use a domain if you have one

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

Save with `Ctrl+X`, `Y`, `Enter`

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/youtube-downloader /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Configure firewall (if UFW is enabled)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
```

### Step 8: Start the Service

```bash
# Enable service to start on boot
sudo systemctl enable youtube-downloader

# Start service
sudo systemctl start youtube-downloader

# Check status
sudo systemctl status youtube-downloader
```

You should see "active (running)" in green.

### Step 9: View Logs

```bash
# Real-time logs
sudo journalctl -u youtube-downloader -f

# Or check log files
tail -f /var/log/youtube-downloader/output.log
tail -f /var/log/youtube-downloader/error.log
```

### Step 10: Test the Service

```bash
# Test health endpoint
curl http://localhost:8080/health

# Should return:
# {"status":"healthy","pytubefix":"available","ffmpeg":"available"}

# Test from external IP (replace YOUR_VPS_IP)
curl http://YOUR_VPS_IP/health
```

---

## Configure Cloud Run

Now that the service is running on Hostinger, configure your Cloud Run backend to use it.

### 1. Update .env File

On your local machine, edit `.env`:

```env
# Add these lines (replace YOUR_VPS_IP with actual IP)
YOUTUBE_DOWNLOADER_URL=http://YOUR_VPS_IP
YOUTUBE_DOWNLOADER_API_KEY=540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55
YOUTUBE_DOWNLOADER_TIMEOUT=300
```

### 2. Deploy Cloud Run

```powershell
.\deploy-backend-simple.ps1
```

### 3. Test Integration

```bash
# Test health endpoint on Cloud Run
curl https://YOUR-CLOUD-RUN-URL.run.app/health
```

Look for this in the response:
```json
{
  "external_youtube_downloader": {
    "configured": true,
    "status": "healthy",
    "url": "http://YOUR_VPS_IP"
  }
}
```

---

## End-to-End Testing

### 1. Test via Frontend

1. Open your frontend: `https://your-frontend.run.app`
2. Go to "Contribute" page
3. Enter a YouTube URL (e.g., https://www.youtube.com/watch?v=jNQXAC9IVRw)
4. Submit

### 2. Monitor Logs

**On Hostinger VPS:**
```bash
sudo journalctl -u youtube-downloader -f
```

**On Cloud Run:**
```bash
gcloud logging tail "resource.type=cloud_run_revision" --limit 50
```

You should see:
- "Using external YouTube downloader service"
- Download progress on VPS
- File upload to GCS
- Status update to PENDING_APPROVAL

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u youtube-downloader -n 50 --no-pager

# Check if port is in use
sudo netstat -tulpn | grep 8080

# Test Python directly
cd /opt/youtube-downloader
source venv/bin/activate
python main.py
```

### Downloads Fail

```bash
# Check ffmpeg
which ffmpeg
ffmpeg -version

# Update pytubefix
cd /opt/youtube-downloader
source venv/bin/activate
pip install --upgrade pytubefix
```

### Cloud Run Can't Connect

1. Verify VPS firewall allows port 80
2. Test from your local machine: `curl http://YOUR_VPS_IP/health`
3. Check API key matches in both .env and service file
4. Check VPS public IP is correct

### Nginx Errors

```bash
# Check Nginx config
sudo nginx -t

# Check Nginx status
sudo systemctl status nginx

# View Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Restart Nginx
sudo systemctl restart nginx
```

---

## Security Enhancements (Optional)

### Setup HTTPS with Let's Encrypt

If you have a domain pointed to your VPS:

```bash
# Install certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d youtube-dl.yourdomain.com

# Update .env to use HTTPS
YOUTUBE_DOWNLOADER_URL=https://youtube-dl.yourdomain.com
```

### Restrict Access to Cloud Run IPs

```bash
# Get Cloud Run IP ranges from Google Cloud
# Then configure UFW to only allow those IPs
sudo ufw allow from CLOUD_RUN_IP to any port 80
```

---

## Useful Commands

```bash
# Service management
sudo systemctl status youtube-downloader
sudo systemctl start youtube-downloader
sudo systemctl stop youtube-downloader
sudo systemctl restart youtube-downloader

# View logs
sudo journalctl -u youtube-downloader -f
tail -f /var/log/youtube-downloader/output.log

# Check resource usage
htop
df -h

# Test API
curl http://localhost:8080/health
curl http://YOUR_VPS_IP/health
```

---

## Summary

**What you deployed:**
- YouTube downloader service running on Hostinger VPS
- Nginx reverse proxy
- systemd service management

**Access URLs:**
- Health check: `http://YOUR_VPS_IP/health`
- API endpoint: `http://YOUR_VPS_IP/download/file`

**API Key:**
```
540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55
```

**Next steps:**
1. Get SSH access to your Hostinger VPS
2. Follow deployment steps above
3. Test the service
4. Update Cloud Run configuration
5. Test end-to-end with a YouTube video

Good luck! 🚀
