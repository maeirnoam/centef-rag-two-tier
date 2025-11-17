"""
Test YouTube video processing pipeline.
This script tests downloading, transcribing, and processing a short YouTube video.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import create_manifest_entry, get_manifest_entry, DocumentStatus
from tools.processing.ingest_youtube import extract_video_id, download_audio_local, upload_to_gcs
import tempfile

# Test with a short public domain video (change this to your test video)
TEST_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Replace with your test video
TEST_TITLE = "Test YouTube Video"

def test_video_id_extraction():
    """Test extracting video ID from URL"""
    print("Testing video ID extraction...")

    test_cases = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=abc123&t=10s", "abc123"),
    ]

    for url, expected in test_cases:
        result = extract_video_id(url)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {url} -> {result} (expected: {expected})")

    print()

def test_youtube_download():
    """Test downloading audio from YouTube"""
    print(f"Testing YouTube download...")
    print(f"URL: {TEST_YOUTUBE_URL}")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"Downloading to: {tmpdir}")
            wav_path = download_audio_local(TEST_YOUTUBE_URL, tmpdir)

            if os.path.exists(wav_path):
                size_mb = os.path.getsize(wav_path) / (1024 * 1024)
                print(f"✓ Download successful!")
                print(f"  File: {wav_path}")
                print(f"  Size: {size_mb:.2f} MB")
            else:
                print(f"✗ File not found: {wav_path}")

    except Exception as e:
        print(f"✗ Download failed: {e}")
        import traceback
        traceback.print_exc()

    print()

def test_full_pipeline():
    """Test the full processing pipeline (download -> upload -> transcribe -> chunk)"""
    print("Testing full pipeline...")
    print("NOTE: This will create actual GCS files and use Speech-to-Text API credits!")
    print()

    response = input("Do you want to proceed with full pipeline test? (y/n): ")
    if response.lower() != 'y':
        print("Skipping full pipeline test.")
        return

    try:
        # Create manifest entry
        print("Creating manifest entry...")
        source_id = f"test_youtube_{extract_video_id(TEST_YOUTUBE_URL)}"

        entry = create_manifest_entry(
            source_id=source_id,
            title=TEST_TITLE,
            source_uri=TEST_YOUTUBE_URL,
            mimetype="video/youtube",
            uploaded_by="test@example.com"
        )
        print(f"✓ Created entry: {source_id}")

        # Run the processing
        print("Running YouTube processing...")
        from tools.processing.ingest_youtube import main as youtube_main

        # Set command line args
        sys.argv = [
            "ingest_youtube.py",
            source_id,
            TEST_YOUTUBE_URL,
            "--language", "en-US",  # Use English for testing
            "--translate", "none",   # Skip translation for faster testing
            "--window", "30"
        ]

        youtube_main()

        # Check result
        entry = get_manifest_entry(source_id)
        print(f"\n✓ Processing complete!")
        print(f"  Status: {entry.status}")
        print(f"  Data path: {entry.data_path}")

        if entry.status == DocumentStatus.ERROR:
            print(f"  Error: {entry.notes}")

    except Exception as e:
        print(f"✗ Full pipeline failed: {e}")
        import traceback
        traceback.print_exc()

    print()

if __name__ == "__main__":
    print("="*60)
    print("YouTube Processing Test Suite")
    print("="*60)
    print()

    # Run tests
    test_video_id_extraction()
    test_youtube_download()
    test_full_pipeline()

    print("="*60)
    print("Tests complete!")
    print("="*60)