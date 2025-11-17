"""
Test the external YouTube downloader service integration.

This script tests:
1. External service connectivity
2. Download functionality
3. File upload to GCS
4. End-to-end integration
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.processing.youtube_downloader_client import (
    download_youtube_via_external_service,
    health_check_external_service,
    is_external_downloader_configured
)
from tools.processing.ingest_youtube import upload_to_gcs, extract_video_id


def test_health_check():
    """Test external service health check"""
    print("=" * 60)
    print("Testing External Service Health Check")
    print("=" * 60)
    
    health = health_check_external_service()
    print(f"Configured: {health.get('configured')}")
    print(f"Status: {health.get('status')}")
    
    if health.get('configured'):
        print(f"URL: {health.get('url')}")
        if health.get('details'):
            print(f"Details: {health.get('details')}")
    
    if health.get('status') != 'healthy':
        print(f"⚠️  External service is not healthy: {health.get('error', 'Unknown')}")
        return False
    
    print("✓ External service is healthy")
    return True


def test_download(youtube_url: str):
    """Test downloading a YouTube video"""
    print("\n" + "=" * 60)
    print("Testing YouTube Download via External Service")
    print("=" * 60)
    
    if not is_external_downloader_configured():
        print("❌ External downloader not configured")
        print("Set YOUTUBE_DOWNLOADER_URL and YOUTUBE_DOWNLOADER_API_KEY in .env")
        return False
    
    video_id = extract_video_id(youtube_url)
    print(f"Video ID: {video_id}")
    print(f"URL: {youtube_url}")
    print()
    
    try:
        print("Requesting download from external service...")
        wav_path, title = download_youtube_via_external_service(youtube_url, video_id)
        
        print(f"✓ Download successful!")
        print(f"  Title: {title}")
        print(f"  File: {wav_path}")
        
        # Check file size
        import os
        file_size = os.path.getsize(wav_path)
        file_size_mb = file_size / 1024 / 1024
        print(f"  Size: {file_size:,} bytes ({file_size_mb:.2f} MB)")
        
        # Verify it's a valid WAV file
        with open(wav_path, 'rb') as f:
            header = f.read(12)
            if header[:4] != b'RIFF' or header[8:12] != b'WAVE':
                print("⚠️  Warning: File doesn't appear to be a valid WAV file")
                return False
        
        print("✓ File is a valid WAV audio file")
        
        # Test upload to GCS
        print("\nTesting upload to GCS...")
        bucket = os.getenv("SOURCE_BUCKET", "centef-rag-bucket").replace("gs://", "").strip("/")
        dest_path = f"test/youtube_{video_id}_test.wav"
        
        gcs_uri = upload_to_gcs(wav_path, bucket, dest_path)
        print(f"✓ Uploaded to: {gcs_uri}")
        
        # Cleanup
        print("\nCleaning up test file from GCS...")
        from google.cloud import storage
        client = storage.Client()
        bucket_obj = client.bucket(bucket)
        blob = bucket_obj.blob(dest_path)
        blob.delete()
        print("✓ Test file deleted from GCS")
        
        return True
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("External YouTube Downloader Service - Integration Test")
    print("=" * 60)
    print()
    
    # Test 1: Health check
    if not test_health_check():
        print("\n❌ Health check failed. Cannot proceed with download test.")
        sys.exit(1)
    
    # Test 2: Download
    # Use a short test video
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    print(f"\nUsing test video: {test_url}")
    
    if not test_download(test_url):
        print("\n❌ Download test failed")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    print("\nExternal YouTube downloader service is working correctly.")
    print("You can now use it from Cloud Run by ensuring these environment variables are set:")
    print("  - YOUTUBE_DOWNLOADER_URL")
    print("  - YOUTUBE_DOWNLOADER_API_KEY")
    print("  - YOUTUBE_DOWNLOADER_TIMEOUT (optional, default 300)")


if __name__ == "__main__":
    # Load .env file first
    import os
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✓ Loaded .env file")
        
        # Debug: Show what was loaded
        print(f"YOUTUBE_DOWNLOADER_URL: {os.getenv('YOUTUBE_DOWNLOADER_URL', 'NOT SET')}")
        print(f"YOUTUBE_DOWNLOADER_API_KEY: {os.getenv('YOUTUBE_DOWNLOADER_API_KEY', 'NOT SET')[:20]}..." if os.getenv('YOUTUBE_DOWNLOADER_API_KEY') else "NOT SET")
        print()
    except ImportError:
        print("⚠️  python-dotenv not installed, using system environment variables")
        print()
    
    main()
