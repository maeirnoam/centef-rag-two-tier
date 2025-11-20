# Quick Deployment Checklist for Hostinger VPS

## 🔑 Your Generated API Key
```
540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55
```

## ✅ Pre-Deployment Checklist

- [ ] Access to Hostinger VPS (https://hpanel.hostinger.com/vps/974700/overview)
- [ ] SSH credentials (IP, username, password/key)
- [ ] VPS is running Ubuntu/Debian Linux
- [ ] You have root or sudo access

## 📋 Quick Setup Steps (Copy-Paste Friendly)

### 1️⃣ Initial VPS Setup (Run on VPS)

```bash
# Update and install dependencies
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv ffmpeg nginx

# Create service directory
sudo mkdir -p /opt/youtube-downloader
sudo chown $USER:$USER /opt/youtube-downloader
cd /opt/youtube-downloader
```

### 2️⃣ Upload Files (From Your Windows Machine)

**Using PowerShell:**
```powershell
cd C:\Users\User\PycharmProjects\centef-rag-fresh
scp apps\youtube_downloader\main.py USERNAME@VPS_IP:/opt/youtube-downloader/
scp apps\youtube_downloader\requirements.txt USERNAME@VPS_IP:/opt/youtube-downloader/
scp apps\youtube_downloader\start.sh USERNAME@VPS_IP:/opt/youtube-downloader/
scp apps\youtube_downloader\stop.sh USERNAME@VPS_IP:/opt/youtube-downloader/
scp apps\youtube_downloader\youtube-downloader.service USERNAME@VPS_IP:/tmp/
```

Replace `USERNAME` and `VPS_IP` with your actual values.

### 3️⃣ Setup Python Environment (Run on VPS)

```bash
cd /opt/youtube-downloader
chmod +x start.sh stop.sh
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

### 4️⃣ Configure Service with API Key (Run on VPS)

```bash
# Edit service file
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

Save: `Ctrl+X` → `Y` → `Enter`

```bash
# Install service
sudo cp /tmp/youtube-downloader.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo mkdir -p /var/log/youtube-downloader
sudo chown www-data:www-data /var/log/youtube-downloader
```

### 5️⃣ Configure Nginx (Run on VPS)

```bash
sudo nano /etc/nginx/sites-available/youtube-downloader
```

Paste (replace YOUR_VPS_IP):
```nginx
server {
    listen 80;
    server_name YOUR_VPS_IP;

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

Save: `Ctrl+X` → `Y` → `Enter`

```bash
# Enable and restart Nginx
sudo ln -s /etc/nginx/sites-available/youtube-downloader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### 6️⃣ Start Service (Run on VPS)

```bash
sudo systemctl enable youtube-downloader
sudo systemctl start youtube-downloader
sudo systemctl status youtube-downloader
```

Should show "active (running)" in green! ✅

### 7️⃣ Test Service (Run on VPS)

```bash
# Test locally
curl http://localhost:8080/health

# Test externally (replace YOUR_VPS_IP)
curl http://YOUR_VPS_IP/health
```

Expected response:
```json
{"status":"healthy","pytubefix":"available","ffmpeg":"available"}
```

### 8️⃣ Update .env File (On Your Local Machine)

Edit `C:\Users\User\PycharmProjects\centef-rag-fresh\.env`

Add/update these lines (replace YOUR_VPS_IP):
```env
YOUTUBE_DOWNLOADER_URL=http://YOUR_VPS_IP
YOUTUBE_DOWNLOADER_API_KEY=540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55
YOUTUBE_DOWNLOADER_TIMEOUT=300
```

### 9️⃣ Deploy to Cloud Run (On Your Local Machine)

```powershell
cd C:\Users\User\PycharmProjects\centef-rag-fresh
.\deploy-backend-simple.ps1
```

### 🔟 Test Integration

```bash
# Test Cloud Run health endpoint
curl https://YOUR-CLOUD-RUN-URL.run.app/health
```

Look for:
```json
{
  "external_youtube_downloader": {
    "configured": true,
    "status": "healthy"
  }
}
```

## 🧪 End-to-End Test

1. Open frontend: `https://your-frontend.run.app`
2. Go to "Contribute" page
3. Test with: `https://www.youtube.com/watch?v=jNQXAC9IVRw`
4. Monitor VPS logs: `sudo journalctl -u youtube-downloader -f`
5. Check GCS for uploaded file
6. Verify manifest status: PENDING_APPROVAL

## 🔍 Troubleshooting Quick Commands

```bash
# View service status
sudo systemctl status youtube-downloader

# View logs
sudo journalctl -u youtube-downloader -f
tail -f /var/log/youtube-downloader/output.log

# Restart service
sudo systemctl restart youtube-downloader

# Check port
sudo netstat -tulpn | grep 8080

# Test Python directly
cd /opt/youtube-downloader && source venv/bin/activate && python main.py
```

## 📝 Summary

**Service URL:** `http://YOUR_VPS_IP`
**API Key:** `540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55`
**Health Check:** `http://YOUR_VPS_IP/health`

**Files Deployed:**
- `/opt/youtube-downloader/main.py`
- `/opt/youtube-downloader/requirements.txt`
- `/etc/systemd/system/youtube-downloader.service`
- `/etc/nginx/sites-available/youtube-downloader`

**Next Steps:**
1. Get your VPS IP from Hostinger panel
2. SSH into VPS and follow steps 1️⃣-7️⃣
3. Update .env with VPS IP (step 8️⃣)
4. Deploy to Cloud Run (step 9️⃣)
5. Test! (step 🔟)

Good luck! 🚀
