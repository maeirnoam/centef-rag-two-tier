"""
Test YouTube extraction methods locally without deploying.
This tests all fallback methods with the provided URL.
"""
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.processing.ingest_youtube import (
    extract_video_id,
    try_get_youtube_captions,
    download_audio_local,
    download_audio_pytube,
    download_audio_with_fallback
)

# Test URL
TEST_URL = "https://www.youtube.com/watch?v=DAmfRNPgtsk"

def test_video_id_extraction():
    """Test extracting video ID from URL"""
    print("=" * 60)
    print("Test 1: Video ID Extraction")
    print("=" * 60)

    video_id = extract_video_id(TEST_URL)
    print(f"URL: {TEST_URL}")
    print(f"Video ID: {video_id}")
    print()
    return video_id


def test_captions(video_id):
    """Test getting YouTube captions"""
    print("=" * 60)
    print("Test 2: YouTube Captions (fastest method)")
    print("=" * 60)

    # Try English captions
    print("Trying to fetch English captions...")
    captions_en = try_get_youtube_captions(TEST_URL, "en")

    if captions_en:
        print(f"[OK] Found {len(captions_en)} English caption segments!")
        print(f"First caption: {captions_en[0]}")
        print()
        return True
    else:
        print("[INFO] No English captions found")
        print()

    # Try Arabic captions
    print("Trying to fetch Arabic captions...")
    captions_ar = try_get_youtube_captions(TEST_URL, "ar")

    if captions_ar:
        print(f"[OK] Found {len(captions_ar)} Arabic caption segments!")
        print(f"First caption: {captions_ar[0]}")
        print()
        return True
    else:
        print("[INFO] No Arabic captions found")
        print()

    return False


def test_audio_downloads():
    """Test audio download methods"""
    print("=" * 60)
    print("Test 3: Audio Download Methods")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Temporary directory: {tmpdir}")
        print()

        # Test yt-dlp
        print("Testing yt-dlp (primary method)...")
        try:
            import yt_dlp
            wav_path = download_audio_local(TEST_URL, tmpdir)
            print(f"[OK] yt-dlp download successful!")
            print(f"  WAV file: {wav_path}")
            print(f"  File exists: {Path(wav_path).exists()}")
            if Path(wav_path).exists():
                size_mb = Path(wav_path).stat().st_size / (1024 * 1024)
                print(f"  Size: {size_mb:.2f} MB")
            print()
            return True
        except Exception as e:
            print(f"[ERROR] yt-dlp failed: {e}")
            print()

        # Test pytube fallback
        print("Testing pytube (fallback method)...")
        try:
            from pytube import YouTube
            wav_path = download_audio_pytube(TEST_URL, tmpdir)
            print(f"[OK] pytube download successful!")
            print(f"  WAV file: {wav_path}")
            print(f"  File exists: {Path(wav_path).exists()}")
            if Path(wav_path).exists():
                size_mb = Path(wav_path).stat().st_size / (1024 * 1024)
                print(f"  Size: {size_mb:.2f} MB")
            print()
            return True
        except Exception as e:
            print(f"[ERROR] pytube failed: {e}")
            print()

        # Test fallback system
        print("Testing combined fallback system...")
        try:
            wav_path = download_audio_with_fallback(TEST_URL, tmpdir)
            print(f"[OK] Fallback system successful!")
            print(f"  WAV file: {wav_path}")
            print(f"  File exists: {Path(wav_path).exists()}")
            if Path(wav_path).exists():
                size_mb = Path(wav_path).stat().st_size / (1024 * 1024)
                print(f"  Size: {size_mb:.2f} MB")
            print()
            return True
        except Exception as e:
            print(f"[ERROR] All methods failed: {e}")
            print()

    return False


def main():
    print("=" * 60)
    print("YouTube Extraction Methods Test")
    print("=" * 60)
    print(f"Testing URL: {TEST_URL}")
    print()

    # Test 1: Video ID extraction
    video_id = test_video_id_extraction()

    # Test 2: Captions (fastest if available)
    has_captions = test_captions(video_id)

    if has_captions:
        print("=" * 60)
        print("RESULT: Video has captions!")
        print("=" * 60)
        print("This video can use the fast caption-based processing.")
        print("No audio download needed - saves time and avoids bot detection!")
        print()
    else:
        print("=" * 60)
        print("RESULT: No captions found - will need audio download")
        print("=" * 60)
        print()

        # Test 3: Audio downloads
        success = test_audio_downloads()

        if success:
            print("=" * 60)
            print("SUCCESS: At least one download method worked!")
            print("=" * 60)
        else:
            print("=" * 60)
            print("FAILURE: All download methods failed")
            print("=" * 60)
            print("This video cannot be processed with current methods.")


if __name__ == "__main__":
    main()