# .env File Update Instructions

## Add YouTube Downloader Configuration

After successfully deploying the YouTube downloader service to your Hostinger VPS, you need to update your `.env` file to enable Cloud Run to use it.

## Steps

1. **Get your VPS IP address** from Hostinger panel:
   - Go to https://hpanel.hostinger.com/vps/974700/overview
   - Look for the public IP address (e.g., `123.456.789.012`)

2. **Edit your `.env` file**:
   - Location: `C:\Users\User\PycharmProjects\centef-rag-fresh\.env`
   - Add or update these lines:

```env
# External YouTube Downloader Service
YOUTUBE_DOWNLOADER_URL=http://YOUR_VPS_IP_HERE
YOUTUBE_DOWNLOADER_API_KEY=540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55
YOUTUBE_DOWNLOADER_TIMEOUT=300
```

3. **Replace `YOUR_VPS_IP_HERE`** with your actual VPS IP address

### Example

If your VPS IP is `123.456.789.012`, your `.env` should have:

```env
# External YouTube Downloader Service
YOUTUBE_DOWNLOADER_URL=http://123.456.789.012
YOUTUBE_DOWNLOADER_API_KEY=540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55
YOUTUBE_DOWNLOADER_TIMEOUT=300
```

### If You Setup HTTPS (Optional)

If you configured a domain and SSL certificate (via Let's Encrypt), use HTTPS instead:

```env
YOUTUBE_DOWNLOADER_URL=https://youtube-dl.yourdomain.com
YOUTUBE_DOWNLOADER_API_KEY=540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55
YOUTUBE_DOWNLOADER_TIMEOUT=300
```

## Deploy to Cloud Run

After updating `.env`, deploy the backend:

```powershell
cd C:\Users\User\PycharmProjects\centef-rag-fresh
.\deploy-backend-simple.ps1
```

## Verify Deployment

Test that Cloud Run can reach your YouTube downloader:

```bash
curl https://YOUR-CLOUD-RUN-URL.run.app/health
```

Look for this section in the response:
```json
{
  "external_youtube_downloader": {
    "configured": true,
    "status": "healthy",
    "url": "http://YOUR_VPS_IP"
  }
}
```

## Important Notes

- **API Key Security**: The API key `540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55` is only known to your VPS service and Cloud Run
- **HTTP vs HTTPS**:
  - HTTP is fine for testing
  - For production, setup HTTPS with Let's Encrypt (see HOSTINGER_DEPLOYMENT_GUIDE.md)
- **Firewall**: Ensure your VPS firewall allows incoming connections on port 80 (and 443 if using HTTPS)

## Troubleshooting

If Cloud Run shows "external_youtube_downloader": { "status": "unreachable" }:

1. Check VPS service is running: `sudo systemctl status youtube-downloader`
2. Check Nginx is running: `sudo systemctl status nginx`
3. Test from another machine: `curl http://YOUR_VPS_IP/health`
4. Check firewall: `sudo ufw status`
5. Verify API key matches in both `.env` and VPS service configuration
