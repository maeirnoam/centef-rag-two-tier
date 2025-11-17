"""
Test the deployed upload APIs directly.
This allows testing video/audio/YouTube uploads without using the web UI.
"""
import requests
import os
import time

# Configuration
API_URL = "https://centef-rag-api-gac7qac6jq-uc.a.run.app"
ADMIN_EMAIL = "admin@centef.org"
ADMIN_PASSWORD = "Admin123!"

def get_auth_token():
    """Login and get authentication token"""
    print("Logging in...")
    response = requests.post(
        f"{API_URL}/auth/login",
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"[OK] Logged in successfully")
        return token
    else:
        print(f"[ERROR] Login failed: {response.status_code}")
        print(response.text)
        return None

def test_youtube_upload(token, youtube_url):
    """Test YouTube video upload"""
    print(f"\nTesting YouTube upload: {youtube_url}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "url": youtube_url,
        "language": "en-US",  # English for testing
        "translate": "ar"     # Translate to Arabic
    }

    response = requests.post(
        f"{API_URL}/upload/youtube",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        data = response.json()
        print(f"[OK] Upload successful!")
        print(f"  Video ID: {data.get('video_id')}")
        print(f"  Source ID: {data.get('source_id')}")
        print(f"  Message: {data.get('message')}")
        return data.get('source_id')
    else:
        print(f"[ERROR] Upload failed: {response.status_code}")
        print(response.text)
        return None

def check_processing_status(token, source_id):
    """Check the processing status of an uploaded item"""
    print(f"\nChecking status for: {source_id}")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Get manifest to check status
    response = requests.get(
        f"{API_URL}/manifest",
        headers=headers
    )

    if response.status_code == 200:
        manifest = response.json()
        for entry in manifest:
            if entry.get('source_id') == source_id:
                print(f"[OK] Found entry:")
                print(f"  Status: {entry.get('status')}")
                print(f"  Title: {entry.get('title')}")
                if entry.get('notes'):
                    print(f"  Notes: {entry.get('notes')}")
                if entry.get('data_path'):
                    print(f"  Data path: {entry.get('data_path')}")
                return entry

        print(f"[ERROR] Entry not found in manifest")
    else:
        print(f"[ERROR] Failed to get manifest: {response.status_code}")

    return None

def test_video_upload(token, video_file_path):
    """Test video file upload"""
    if not os.path.exists(video_file_path):
        print(f"[ERROR] Video file not found: {video_file_path}")
        return None

    print(f"\nTesting video upload: {video_file_path}")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    files = {
        "file": open(video_file_path, "rb")
    }

    data = {
        "language": "en-US",
        "translate": "ar"
    }

    response = requests.post(
        f"{API_URL}/upload/video",
        headers=headers,
        files=files,
        data=data
    )

    if response.status_code == 200:
        result = response.json()
        print(f"[OK] Upload successful!")
        print(f"  Source ID: {result.get('source_id')}")
        print(f"  Message: {result.get('message')}")
        return result.get('source_id')
    else:
        print(f"[ERROR] Upload failed: {response.status_code}")
        print(response.text)
        return None

def main():
    print("="*60)
    print("Upload API Test")
    print("="*60)

    # Get auth token
    token = get_auth_token()
    if not token:
        print("Cannot proceed without authentication")
        return

    # Test YouTube upload with a short public domain video
    print("\n" + "="*60)
    print("Test 1: YouTube Upload")
    print("="*60)

    # Using a very short (10 seconds) Creative Commons video for testing
    test_url = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"  # Big Buck Bunny trailer (short)
    # Or use your own test video URL

    print(f"Using test video: {test_url}")
    print("Note: You can change this URL in the script to test with your own video")
    print()

    response = input("Proceed with YouTube upload test? (y/n): ")
    if response.lower() == 'y':
        source_id = test_youtube_upload(token, test_url)

        if source_id:
            print("\nWaiting 5 seconds before checking status...")
            time.sleep(5)
            check_processing_status(token, source_id)

            print("\nNote: Background processing continues...")
            print("Check the manifest page or logs to see when processing completes")

    # Test video file upload (if you have a local video file)
    print("\n" + "="*60)
    print("Test 2: Video File Upload")
    print("="*60)

    video_path = input("Enter path to video file (or press Enter to skip): ").strip()
    if video_path:
        source_id = test_video_upload(token, video_path)

        if source_id:
            print("\nWaiting 5 seconds before checking status...")
            time.sleep(5)
            check_processing_status(token, source_id)
    else:
        print("Skipping video file upload test")

    print("\n" + "="*60)
    print("Tests complete!")
    print("="*60)

if __name__ == "__main__":
    main()