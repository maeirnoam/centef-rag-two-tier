"""
Setup YouTube Cookies for yt-dlp.

This script helps you export cookies from your browser to use with yt-dlp
to bypass bot detection when downloading YouTube videos.

Usage:
    python tools/setup_youtube_oauth.py

The cookies will be saved and can be uploaded to Cloud Run.
"""
import os
import sys
import subprocess
from pathlib import Path

print("=" * 80)
print("YouTube Cookie Export for yt-dlp")
print("=" * 80)
print()

# Check if yt-dlp is installed
try:
    result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
    print(f"✓ yt-dlp version: {result.stdout.strip()}")
except FileNotFoundError:
    print("❌ yt-dlp not found. Install with: pip install yt-dlp")
    sys.exit(1)

print()
print("This will export cookies from your browser for YouTube authentication.")
print()

# Create cache directory
cache_dir = Path.home() / ".cache" / "yt-dlp"
cache_dir.mkdir(parents=True, exist_ok=True)
cookies_file = cache_dir / "youtube_cookies.txt"

print(f"Cookies will be saved to: {cookies_file}")
print()

# Prompt for browser choice
print("Available browsers:")
print("  1. Chrome")
print("  2. Firefox")
print("  3. Edge")
print("  4. Opera")
print()
browser_choice = input("Enter browser number (1-4): ").strip()

browser_map = {
    "1": "chrome",
    "2": "firefox",
    "3": "edge",
    "4": "opera"
}

if browser_choice not in browser_map:
    print("Invalid choice!")
    sys.exit(1)

browser = browser_map[browser_choice]
print(f"\nUsing browser: {browser}")
print()

# Use a simple test download to export cookies
test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - first YouTube video

print("Exporting cookies from browser...")
print("(You must be signed in to YouTube in your browser)")
print()

cmd = [
    "yt-dlp",
    "--cookies-from-browser", browser,
    "--cookies", str(cookies_file),
    "--skip-download",
    test_url
]

print(f"Running: {' '.join(cmd)}")
print()

try:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    print(result.stdout)
    print()
    print("=" * 80)
    print("✓ Cookie export successful!")
    print("=" * 80)
    print()
    print(f"Cookies saved to: {cookies_file}")
    print()
    print("Next steps:")
    print()
    print("1. For local testing, set environment variable:")
    print(f"   $env:YOUTUBE_COOKIES_FILE = '{cookies_file}'")
    print()
    print("2. For Cloud Run deployment:")
    print(f"   - Upload {cookies_file} to GCS")
    print("   - Set YOUTUBE_COOKIES_FILE environment variable in Cloud Run")
    print()
    print("Example GCS upload command:")
    print(f"   gsutil cp {cookies_file} gs://centef-rag-bucket/yt-dlp-cookies/youtube_cookies.txt")
    print()
    print("Then add to .env:")
    print("   YOUTUBE_COOKIES_BUCKET=centef-rag-bucket")
    print()
    
except subprocess.CalledProcessError as e:
    print()
    print("=" * 80)
    print("❌ Cookie export failed")
    print("=" * 80)
    print()
    print(f"Error output: {e.stderr}")
    print()
    print("Troubleshooting:")
    print("- Make sure you're signed in to YouTube in your browser")
    print("- Try closing and reopening your browser")
    print("- Make sure the browser is fully closed before running this script")
    print("- Try a different browser")
    sys.exit(1)
