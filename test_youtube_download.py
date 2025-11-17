"""
Test YouTube download with yt-dlp to verify cookies and configuration work.
This script tests ONLY the download step without uploading to GCS.
"""
import os
import sys
import logging
import tempfile
from pathlib import Path

# Set up environment
os.environ["YOUTUBE_COOKIES_FILE"] = str(Path.home() / ".cache" / "yt-dlp" / "youtube_cookies.txt")

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.processing.ingest_youtube import download_audio_local

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_download(youtube_url: str):
    """Test downloading a YouTube video with current configuration."""
    
    logger.info("=" * 60)
    logger.info("YouTube Download Test")
    logger.info("=" * 60)
    logger.info(f"URL: {youtube_url}")
    
    # Check cookies file
    cookies_file = os.getenv("YOUTUBE_COOKIES_FILE")
    if cookies_file and os.path.exists(cookies_file):
        file_size = os.path.getsize(cookies_file)
        logger.info(f"✓ Cookies file found: {cookies_file}")
        logger.info(f"  Size: {file_size} bytes")
        
        # Read first few lines to verify format
        with open(cookies_file, 'r') as f:
            lines = f.readlines()[:5]
            logger.info(f"  First lines preview:")
            for line in lines:
                logger.info(f"    {line.strip()[:80]}...")
    else:
        logger.error(f"✗ Cookies file not found: {cookies_file}")
        logger.error("  Run: python tools/setup_youtube_oauth.py")
        return False
    
    logger.info("")
    logger.info("Starting download test...")
    logger.info("")
    
    # Create temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            wav_path = download_audio_local(youtube_url, temp_dir)
            
            if os.path.exists(wav_path):
                file_size_mb = os.path.getsize(wav_path) / (1024 * 1024)
                logger.info("")
                logger.info("=" * 60)
                logger.info("✓ SUCCESS!")
                logger.info("=" * 60)
                logger.info(f"Downloaded file: {wav_path}")
                logger.info(f"File size: {file_size_mb:.2f} MB")
                logger.info("")
                logger.info("Your configuration is working correctly!")
                logger.info("You can now deploy to Cloud Run.")
                return True
            else:
                logger.error("")
                logger.error("=" * 60)
                logger.error("✗ FAILED")
                logger.error("=" * 60)
                logger.error("Download completed but file not found")
                return False
                
        except Exception as e:
            logger.error("")
            logger.error("=" * 60)
            logger.error("✗ FAILED")
            logger.error("=" * 60)
            logger.error(f"Error: {type(e).__name__}: {e}")
            logger.error("")
            logger.error("Common issues:")
            logger.error("1. Cookies expired - re-export from Firefox")
            logger.error("2. Video is private/restricted")
            logger.error("3. Network connectivity issues")
            logger.error("4. YouTube changed their API")
            logger.error("")
            logger.error("Try re-exporting cookies:")
            logger.error("  python tools/setup_youtube_oauth.py")
            return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test YouTube download with yt-dlp")
    parser.add_argument("url", help="YouTube video URL to test")
    args = parser.parse_args()
    
    success = test_download(args.url)
    sys.exit(0 if success else 1)
