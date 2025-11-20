# Deploy YouTube Downloader to Your Hostinger VPS
# IP: 145.223.73.61

## Step 1: Connect to VPS

Open a new terminal/PowerShell and connect:

```bash
ssh root@145.223.73.61
```

Enter your root password when prompted.

---

## Step 2: Prepare VPS (Run these commands on VPS)

Copy and paste these commands one by one:

```bash
# Update system
apt-get update && apt-get upgrade -y

# Install dependencies
apt-get install -y python3 python3-pip python3-venv ffmpeg nginx

# Verify installations
python3 --version
ffmpeg -version

# Create service directory
mkdir -p /opt/youtube-downloader
cd /opt/youtube-downloader
```

---

## Step 3: Upload Files from Windows

**Keep the SSH session open**, but open a NEW PowerShell window on your Windows machine.

In the new PowerShell window, run:

```powershell
cd C:\Users\User\PycharmProjects\centef-rag-fresh

# Upload main files
scp apps\youtube_downloader\main.py root@145.223.73.61:/opt/youtube-downloader/
scp apps\youtube_downloader\requirements.txt root@145.223.73.61:/opt/youtube-downloader/
scp apps\youtube_downloader\start.sh root@145.223.73.61:/opt/youtube-downloader/
scp apps\youtube_downloader\stop.sh root@145.223.73.61:/opt/youtube-downloader/
scp apps\youtube_downloader\youtube-downloader.service root@145.223.73.61:/tmp/
```

Enter your root password when prompted for each file.

---

## Step 4: Setup Python Environment (Back on VPS)

Go back to your VPS SSH session and run:

```bash
cd /opt/youtube-downloader

# Make scripts executable
chmod +x start.sh stop.sh

# Create Python virtual environment
python3 -m venv venv

# Activate and install packages
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Verify installations
pip list | grep -E "fastapi|uvicorn|pytubefix"

# Deactivate for now
deactivate
```

---

## Step 5: Configure Service with API Key (On VPS)

```bash
# Edit service file
nano /tmp/youtube-downloader.service
```

Find this line:
```
Environment="YOUTUBE_DOWNLOADER_API_KEY=CHANGE_ME_TO_STRONG_RANDOM_KEY"
```

Replace with:
```
Environment="YOUTUBE_DOWNLOADER_API_KEY=540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55"
```

Save: Press `Ctrl+X`, then `Y`, then `Enter`

Then run:

```bash
# Install service
cp /tmp/youtube-downloader.service /etc/systemd/system/
systemctl daemon-reload

# Create log directory
mkdir -p /var/log/youtube-downloader
chown www-data:www-data /var/log/youtube-downloader
```

---

## Step 6: Configure Nginx (On VPS)

```bash
# Create Nginx config
nano /etc/nginx/sites-available/youtube-downloader
```

Paste this configuration:

```nginx
server {
    listen 80;
    server_name 145.223.73.61;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 500M;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

Save: Press `Ctrl+X`, then `Y`, then `Enter`

Then run:

```bash
# Enable site
ln -s /etc/nginx/sites-available/youtube-downloader /etc/nginx/sites-enabled/

# Test Nginx config
nginx -t

# Restart Nginx
systemctl restart nginx

# Configure firewall (if UFW is active)
ufw allow 80/tcp
ufw allow 443/tcp
```

---

## Step 7: Start the Service (On VPS)

```bash
# Enable service to start on boot
systemctl enable youtube-downloader

# Start service
systemctl start youtube-downloader

# Check status (should show "active (running)" in green)
systemctl status youtube-downloader
```

---

## Step 8: Test the Service (On VPS)

```bash
# Test locally
curl http://localhost:8080/health

# Test externally
curl http://145.223.73.61/health
```

Both should return:
```json
{"status":"healthy","pytubefix":"available","ffmpeg":"available"}
```

If you see this, SUCCESS! ✅

---

## Step 9: Update .env File (On Windows)

On your Windows machine, edit:
`C:\Users\User\PycharmProjects\centef-rag-fresh\.env`

Add or update these lines:

```env
YOUTUBE_DOWNLOADER_URL=http://145.223.73.61
YOUTUBE_DOWNLOADER_API_KEY=540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55
YOUTUBE_DOWNLOADER_TIMEOUT=300
```

---

## Step 10: Deploy to Cloud Run (On Windows)

```powershell
cd C:\Users\User\PycharmProjects\centef-rag-fresh
.\deploy-backend-simple.ps1
```

---

## Step 11: Test Everything (On Windows)

```powershell
# Test VPS connection
python test_hostinger_youtube_downloader.py
```

When prompted, enter: `145.223.73.61`

---

## Useful Commands for Later

**View logs on VPS:**
```bash
# Real-time logs
sudo journalctl -u youtube-downloader -f

# Log files
tail -f /var/log/youtube-downloader/output.log
tail -f /var/log/youtube-downloader/error.log
```

**Restart service on VPS:**
```bash
sudo systemctl restart youtube-downloader
```

**Check service status on VPS:**
```bash
sudo systemctl status youtube-downloader
```

---

## Troubleshooting

If service won't start:
```bash
journalctl -u youtube-downloader -n 50
```

If Nginx errors:
```bash
nginx -t
systemctl status nginx
```

If downloads fail:
```bash
cd /opt/youtube-downloader
source venv/bin/activate
pip install --upgrade pytubefix
```

---

## Summary

**VPS IP:** 145.223.73.61
**Service URL:** http://145.223.73.61
**API Key:** 540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55
**Health Check:** http://145.223.73.61/health

You're all set! Follow the steps above in order, and your YouTube downloader will be running on Hostinger. 🚀
