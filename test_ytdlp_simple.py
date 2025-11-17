"""
Simple test to check if yt-dlp can access YouTube with cookies.
Just extracts info without downloading.
"""
import os
import sys
from pathlib import Path

# Set cookies path
cookies_path = Path.home() / ".cache" / "yt-dlp" / "youtube_cookies.txt"
print(f"Cookies file: {cookies_path}")
print(f"Exists: {cookies_path.exists()}")

if cookies_path.exists():
    print(f"Size: {cookies_path.stat().st_size} bytes")
    print()

# Test with yt-dlp
try:
    import yt_dlp
    
    test_url = "https://www.youtube.com/watch?v=qaGYZD2tWKM"
    print(f"Testing URL: {test_url}")
    print()
    
    # Firefox user agent matching the cookies
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"
    
    ydl_opts = {
        "quiet": False,
        "verbose": True,
        "skip_download": True,  # Just test info extraction
        "user_agent": user_agent,
        "http_headers": {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "DNT": "1",
        },
        "extractor_args": {"youtube": {"player_client": ["web"]}},
    }
    
    # Add cookies if file exists
    if cookies_path.exists():
        ydl_opts["cookiefile"] = str(cookies_path)
        print(f"✓ Using cookies: {cookies_path}")
    else:
        print(f"✗ No cookies file found")
    
    print()
    print("=" * 60)
    print("Attempting to extract video info...")
    print("=" * 60)
    print()
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(test_url, download=False)
        
        print()
        print("=" * 60)
        print("✓ SUCCESS!")
        print("=" * 60)
        print(f"Title: {info.get('title')}")
        print(f"Duration: {info.get('duration')} seconds")
        print(f"Uploader: {info.get('uploader')}")
        print()
        print("Configuration is working! You can now deploy.")
        
except Exception as e:
    print()
    print("=" * 60)
    print("✗ FAILED")
    print("=" * 60)
    print(f"Error: {type(e).__name__}")
    print(f"Message: {e}")
    print()
    print("This suggests the cookies may be expired or invalid.")
    print("Try re-exporting cookies from Firefox:")
    print("  1. Open Firefox")
    print("  2. Go to youtube.com and make sure you're logged in")
    print("  3. Close Firefox")
    print("  4. Run: python tools/setup_youtube_oauth.py")
    sys.exit(1)
