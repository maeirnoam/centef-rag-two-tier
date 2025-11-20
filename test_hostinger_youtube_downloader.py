"""
Test script for Hostinger YouTube Downloader deployment.
Run this after deploying to verify the service is working.
"""
import os
import requests
import sys

# Configuration
API_KEY = "540cb0e8711ecf1e772b6270f97ea81836bf4a7f2eb5186b9dd34bb70a612e55"
VPS_IP = "145.223.73.61"#input("Enter your Hostinger VPS IP address: ").strip()
BASE_URL = f"http://{VPS_IP}:8080"

print("=" * 70)
print("YouTube Downloader Service - Hostinger VPS Test")
print("=" * 70)
print(f"Testing service at: {BASE_URL}")
print()

# Test 1: Basic connectivity
print("Test 1: Basic Connectivity")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}/", timeout=10)
    if response.status_code == 200:
        print("✓ Service is reachable")
        print(f"  Response: {response.json()}")
    else:
        print(f"✗ Unexpected status code: {response.status_code}")
        print(f"  Response: {response.text}")
except requests.exceptions.ConnectionError:
    print(f"✗ Cannot connect to {BASE_URL}")
    print("  Possible issues:")
    print("  - VPS IP is incorrect")
    print("  - Service is not running")
    print("  - Firewall is blocking port 80")
    print("  - Nginx is not configured correctly")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

print()

# Test 2: Health check
print("Test 2: Health Check")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}/health", timeout=10)
    if response.status_code == 200:
        health = response.json()
        print("✓ Health check passed")
        print(f"  Status: {health.get('status')}")
        print(f"  pytubefix: {health.get('pytubefix')}")
        print(f"  ffmpeg: {health.get('ffmpeg')}")

        if health.get('pytubefix') != 'available':
            print("  ⚠️ Warning: pytubefix is not available!")
    else:
        print(f"✗ Health check failed: {response.status_code}")
        print(f"  Response: {response.text}")
except Exception as e:
    print(f"✗ Error: {e}")

print()

# Test 3: API key authentication
print("Test 3: API Key Authentication")
print("-" * 70)
try:
    # # Test with wrong API key (should fail)
    # response = requests.post(
    #     f"{BASE_URL}/download",
    #     headers={
    #         "X-API-Key": "wrong-key",
    #         "Content-Type": "application/json"
    #     },
    #     json={
    #         "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    #         "video_id": "test123"
    #     },
    #     timeout=10
    # )

    # if response.status_code == 401:
    #     print("✓ Authentication works (rejected wrong API key)")
    # else:
    #     print(f"⚠️ Unexpected response with wrong key: {response.status_code}")

    # Test with correct API key (should work)
    response = requests.post(
        f"{BASE_URL}/download",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
            "video_id": "test123"
        },
        timeout=120
    )

    if response.status_code == 200:
        print("✓ Authentication passed with correct API key")
        result = response.json()
        if result.get('success'):
            print(f"  Video title: {result.get('title')}")
        else:
            print(f"  ⚠️ Download reported failure: {result.get('error')}")
    else:
        print(f"✗ Request failed: {response.status_code}")
        print(f"  Response: {response.text}")

except Exception as e:
    print(f"✗ Error: {e}")

print()

# Test 4: File download endpoint (quick test)
print("Test 4: File Download Endpoint (Small Video)")
print("-" * 70)
print("⚠️ This test downloads a short video - may take 30-60 seconds")

test_download = input("Run download test? (y/n): ").strip().lower()

if test_download == 'y':
    try:
        # Use a very short video for testing
        response = requests.post(
            f"{BASE_URL}/download/file",
            headers={
                "X-API-Key": API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # "Me at the zoo" - first YouTube video, 19 seconds
                "video_id": "test_video"
            },
            timeout=120,
            stream=True
        )

        if response.status_code == 200:
            # Get video title from headers
            video_title = response.headers.get('X-Video-Title', 'Unknown')
            import urllib.parse
            video_title = urllib.parse.unquote(video_title)

            # Check content type
            content_type = response.headers.get('Content-Type', '')

            # Get file size
            content_length = response.headers.get('Content-Length', '0')
            file_size_mb = int(content_length) / 1024 / 1024 if content_length.isdigit() else 0

            print("✓ Download successful!")
            print(f"  Video title: {video_title}")
            print(f"  Content type: {content_type}")
            print(f"  File size: {file_size_mb:.2f} MB")

            # Save a small sample to verify it's a valid file
            sample_file = "test_download.wav"
            with open(sample_file, 'wb') as f:
                chunk = next(response.iter_content(chunk_size=8192), None)
                if chunk:
                    f.write(chunk)

            print(f"  Sample saved to: {sample_file}")
            print("  (Only first chunk saved to avoid large download)")

        else:
            print(f"✗ Download failed: {response.status_code}")
            print(f"  Response: {response.text[:500]}")

    except requests.exceptions.Timeout:
        print("✗ Request timed out (video download took too long)")
        print("  This might be normal for longer videos or slow connections")
    except Exception as e:
        print(f"✗ Error: {e}")
else:
    print("  Skipped")

print()
print("=" * 70)
print("Summary")
print("=" * 70)
print(f"Service URL: {BASE_URL}")
print(f"API Key: {API_KEY}")
print()
print("Next steps:")
print("1. If all tests passed, update your .env file with:")
print(f"   YOUTUBE_DOWNLOADER_URL={BASE_URL}")
print(f"   YOUTUBE_DOWNLOADER_API_KEY={API_KEY}")
print("2. Deploy Cloud Run with: .\\deploy-backend-simple.ps1")
print("3. Test end-to-end via frontend")
print()
print("If tests failed, check:")
print("- sudo systemctl status youtube-downloader")
print("- sudo journalctl -u youtube-downloader -f")
print("- sudo nginx -t && sudo systemctl status nginx")
print("=" * 70)
