# YouTube Cookies Setup for yt-dlp

Since YouTube blocks bot requests, we need to use browser cookies to authenticate yt-dlp.

## Method 1: Export Cookies with Browser Extension (Recommended)

### Step 1: Install Cookie Export Extension

**For Chrome/Edge:**
- Install "Get cookies.txt LOCALLY" extension: https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc

**For Firefox:**
- Install "cookies.txt" extension: https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/

### Step 2: Export YouTube Cookies

1. Go to https://www.youtube.com (make sure you're signed in)
2. Click the extension icon
3. Click "Export" or "Download"
4. Save the file as `youtube_cookies.txt`

### Step 3: Upload to GCS

```powershell
# Create directory in GCS
gsutil mb -p sylvan-faculty-476113-c9 gs://centef-rag-bucket/yt-dlp-cookies/ 2>$null

# Upload cookies file
gsutil cp youtube_cookies.txt gs://centef-rag-bucket/yt-dlp-cookies/youtube_cookies.txt
```

### Step 4: Add to .env File

Add this line to your `.env` file:
```
YOUTUBE_COOKIES_BUCKET=centef-rag-bucket
```

### Step 5: Redeploy Backend

```powershell
.\deploy-backend-simple.ps1
```

## Method 2: Close Chrome and Use yt-dlp (Alternative)

If you prefer to use yt-dlp directly:

1. **Close Chrome completely** (check Task Manager to make sure no Chrome processes are running)
2. Run: `python tools\setup_youtube_oauth.py`
3. Choose Chrome (1) when prompted
4. Follow the upload instructions from the script output

## Testing Locally

After exporting cookies, test locally:

```powershell
# Set environment variable
$env:YOUTUBE_COOKIES_FILE = "$env:USERPROFILE\.cache\yt-dlp\youtube_cookies.txt"

# Test download
python tools/processing/ingest_youtube.py test_video "https://www.youtube.com/watch?v=jNQXAC9IVRw" --language en-US --translate none
```

## Troubleshooting

### "Could not copy Chrome cookie database"
- Chrome is running. Close Chrome completely (including background processes)
- Check Task Manager for any Chrome processes
- Try Edge or Firefox instead

### "Sign in to confirm you're not a bot"
- Cookies are invalid or expired
- Re-export cookies from browser
- Make sure you're signed in to YouTube before exporting

### Cookies expire after ~6 months
- Re-export cookies periodically
- Upload new cookies to GCS
- Redeploy backend

## Security Note

The cookies file contains your YouTube session. Keep it secure:
- Don't commit it to Git
- Store in GCS with restricted access
- Rotate cookies periodically
