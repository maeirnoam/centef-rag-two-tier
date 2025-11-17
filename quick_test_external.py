"""Quick test of external YouTube downloader"""
import os
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("Quick External Downloader Test")
print("=" * 60)
print()

# Check environment
url = os.getenv("YOUTUBE_DOWNLOADER_URL")
key = os.getenv("YOUTUBE_DOWNLOADER_API_KEY")

print(f"URL: {url}")
print(f"API Key: {key[:20]}..." if key else "NOT SET")
print()

if not url or not key:
    print("❌ Environment variables not set!")
    print("Make sure .env has:")
    print("  YOUTUBE_DOWNLOADER_URL=http://127.0.0.1:8080")
    print("  YOUTUBE_DOWNLOADER_API_KEY=local-test-key-12345")
    exit(1)

# Test health
print("Testing health check...")
import requests
try:
    response = requests.get(f"{url}/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Health check passed")
        print(f"  Status: {data.get('status')}")
        print(f"  Pytubefix: {data.get('pytubefix')}")
    else:
        print(f"❌ Health check failed: {response.status_code}")
        exit(1)
except Exception as e:
    print(f"❌ Cannot connect: {e}")
    print("Make sure the external service is running on http://127.0.0.1:8080")
    exit(1)

print()
print("✓ External service is working!")
print()
print("Now test with integration:")
print("  from tools.processing.youtube_downloader_client import download_youtube_via_external_service")
print("  wav_path, title = download_youtube_via_external_service('https://www.youtube.com/watch?v=jNQXAC9IVRw', 'test123')")
