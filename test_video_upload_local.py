"""
Test video upload and processing locally before deploying to Cloud Run
"""
import requests
import time
import json
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
BACKEND_URL = "http://localhost:8080"  # Local backend
VIDEO_GCS_URI = "gs://centef-rag-bucket/sources/test_whatsapp_video.mp4"
VIDEO_FILENAME = "test_whatsapp_video.mp4"

# Test credentials (from your .env file)
TEST_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@example.com")
TEST_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin123")

print("=" * 60)
print("Testing Video Upload API (Local Backend)")
print("=" * 60)

# Step 1: Login
print(f"\n[1/4] Logging in as {TEST_EMAIL}...")
login_response = requests.post(
    f"{BACKEND_URL}/auth/login",
    json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"✓ Login successful! Token: {token[:20]}...")

# Step 2: Upload video file
print(f"\n[2/4] Uploading video file...")
print(f"Reading video from GCS: {VIDEO_GCS_URI}")

# Download from GCS to temp file
from google.cloud import storage
import tempfile

client = storage.Client()
bucket = client.bucket("centef-rag-bucket")
blob = bucket.blob("sources/test_whatsapp_video.mp4")

with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
    blob.download_to_filename(tmp.name)
    temp_video_path = tmp.name
    print(f"Downloaded to temp file: {temp_video_path}")

# Upload via API
with open(temp_video_path, "rb") as f:
    files = {"file": (VIDEO_FILENAME, f, "video/mp4")}
    data = {"language": "ar-SA", "translate": "en"}

    upload_response = requests.post(
        f"{BACKEND_URL}/upload/video",
        files=files,
        data=data,
        headers=headers
    )

# Clean up temp file
os.unlink(temp_video_path)

if upload_response.status_code != 200:
    print(f"❌ Upload failed: {upload_response.status_code}")
    print(upload_response.text)
    exit(1)

upload_data = upload_response.json()
source_id = upload_data["source_id"]
print(f"✓ Upload successful!")
print(f"  Source ID: {source_id}")
print(f"  Status: {upload_data['status']}")
print(f"  Message: {upload_data['message']}")

# Step 3: Monitor processing status
print(f"\n[3/4] Monitoring processing status...")
print("Waiting for background processing to complete...")

for i in range(60):  # Wait up to 5 minutes
    time.sleep(5)

    # Get manifest entry
    manifest_response = requests.get(
        f"{BACKEND_URL}/admin/manifest",
        headers=headers
    )

    if manifest_response.status_code == 200:
        manifest = manifest_response.json()
        entry = next((e for e in manifest if e["source_id"] == source_id), None)

        if entry:
            status = entry["status"]
            print(f"  [{i*5}s] Status: {status}")

            if status in ["ready", "error"]:
                print(f"\n✓ Processing complete with status: {status}")
                if "notes" in entry:
                    print(f"  Notes: {entry['notes']}")
                break
        else:
            print(f"  [{i*5}s] Entry not found in manifest")
    else:
        print(f"  [{i*5}s] Failed to fetch manifest")

# Step 4: Test query
print(f"\n[4/4] Testing query with processed video...")
query_response = requests.post(
    f"{BACKEND_URL}/query",
    json={
        "query": "ما هو موضوع الفيديو؟",  # "What is the topic of the video?"
        "filters": [{"field": "source_id", "value": source_id}]
    },
    headers=headers
)

if query_response.status_code == 200:
    result = query_response.json()
    print(f"✓ Query successful!")
    print(f"  Answer: {result.get('answer', 'No answer')[:200]}")
    print(f"  Sources: {len(result.get('sources', []))} chunks retrieved")
else:
    print(f"❌ Query failed: {query_response.status_code}")
    print(query_response.text)

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)