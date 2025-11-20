"""
YouTube Downloader Service - External API
Runs on hstgr (non-cloud IP) to bypass YouTube bot detection.

This service:
1. Receives YouTube URL from Cloud Run
2. Downloads audio using yt-dlp through Tor proxy
3. Returns the audio file to Cloud Run

No GCS credentials needed - Cloud Run handles storage.
Requires: yt-dlp, ffmpeg, and Tor service running
"""
import os
import tempfile
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="YouTube Downloader Service",
    description="External service for downloading YouTube audio (bypasses cloud IP detection)",
    version="1.0.0"
)

# Security: API Key authentication
API_KEY = os.getenv("YOUTUBE_DOWNLOADER_API_KEY", "change-me-in-production")

# We use yt-dlp via subprocess instead of importing it
# No need to import pytubefix anymore


class DownloadRequest(BaseModel):
    """Request to download YouTube video audio"""
    url: HttpUrl
    video_id: str


class DownloadResponse(BaseModel):
    """Response with download status"""
    success: bool
    video_id: str
    title: Optional[str] = None
    error: Optional[str] = None


def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Verify API key from request header"""
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return True


def download_youtube_audio(youtube_url: str, out_dir: str) -> tuple[str, str]:
    """
    Download YouTube audio using yt-dlp through Tor proxy.
    Returns: (wav_path, video_title)
    """
    logger.info(f"Starting download with yt-dlp (via Tor): {youtube_url}")

    try:
        import subprocess
        import json
        import glob

        # Use venv's yt-dlp if available, fallback to system
        yt_dlp_path = '/opt/youtube-downloader/venv/bin/yt-dlp'
        if not os.path.exists(yt_dlp_path):
            yt_dlp_path = 'yt-dlp'  # Fallback to system PATH

        # First, get video info
        logger.info("Fetching video metadata...")
        info_cmd = [
            yt_dlp_path,
            '--proxy', 'socks5://127.0.0.1:9050',  # Use Tor
            '--dump-json',
            '--no-warnings',
            youtube_url
        ]

        result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to get video info: {result.stderr}")

        video_info = json.loads(result.stdout)
        title = video_info.get('title', 'Unknown')
        logger.info(f"Video title: {title}")

        # Download audio
        audio_file = os.path.join(out_dir, "audio_raw.%(ext)s")
        logger.info(f"Downloading audio...")

        download_cmd = [
            yt_dlp_path,
            '--proxy', 'socks5://127.0.0.1:9050',  # Use Tor
            '-f', 'bestaudio',
            '-o', audio_file,
            '--no-warnings',
            youtube_url
        ]

        result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=7200)  # 2 hours for very long videos

        if result.returncode != 0:
            raise RuntimeError(f"Download failed: {result.stderr}")

        # Find the downloaded file
        downloaded_files = glob.glob(os.path.join(out_dir, "audio_raw.*"))
        if not downloaded_files:
            raise RuntimeError("Download completed but file not found")

        downloaded_file = downloaded_files[0]
        logger.info(f"Download complete: {downloaded_file}")

        # Convert to 16kHz mono WAV with ffmpeg
        wav_path = os.path.join(out_dir, "audio.wav")

        cmd = [
            "ffmpeg", "-y", "-i", downloaded_file,
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            wav_path
        ]

        logger.info("Converting to WAV format...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"✓ Conversion successful: {wav_path}")

        # Get file size for logging
        file_size = os.path.getsize(wav_path)
        logger.info(f"WAV file size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")

        return wav_path, title

    except Exception as e:
        logger.error(f"Download failed: {e}", exc_info=True)
        raise


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "YouTube Downloader",
        "status": "running",
        "method": "yt-dlp + Tor"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    import subprocess

    # Check yt-dlp (try venv first, then system PATH)
    try:
        yt_dlp_path = '/opt/youtube-downloader/venv/bin/yt-dlp'
        if not os.path.exists(yt_dlp_path):
            yt_dlp_path = 'yt-dlp'
        result = subprocess.run([yt_dlp_path, '--version'], capture_output=True, timeout=5, text=True)
        ytdlp_status = "available" if result.returncode == 0 else "missing"
    except:
        ytdlp_status = "missing"

    # Check Tor
    try:
        result = subprocess.run(['systemctl', 'is-active', 'tor'], capture_output=True, timeout=5, text=True)
        tor_status = "running" if result.returncode == 0 and result.stdout.strip() == 'active' else "not running"
    except:
        tor_status = "unknown"

    # Check ffmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5, text=True)
        ffmpeg_status = "available" if result.returncode == 0 else "missing"
    except:
        ffmpeg_status = "missing"

    return {
        "status": "healthy",
        "ytdlp": ytdlp_status,
        "tor": tor_status,
        "ffmpeg": ffmpeg_status
    }


@app.post("/download", response_model=DownloadResponse)
async def download_youtube(
    request: DownloadRequest,
    x_api_key: str = Header(alias="X-API-Key", default=None)
):
    """
    Download YouTube video audio and return metadata.
    
    Headers:
        X-API-Key: API key for authentication
    
    Request Body:
        url: YouTube video URL
        video_id: Video ID (for tracking)
    
    Returns:
        DownloadResponse with success status and error if any
    """
    # Verify API key
    verify_api_key(x_api_key)
    
    logger.info(f"=" * 60)
    logger.info(f"Download request received: {request.video_id}")
    logger.info(f"URL: {request.url}")
    logger.info(f"=" * 60)
    
    try:
        # Create temporary directory for download
        with tempfile.TemporaryDirectory() as tmpdir:
            logger.info(f"Using temp directory: {tmpdir}")
            
            # Download and convert audio
            wav_path, title = download_youtube_audio(str(request.url), tmpdir)
            
            logger.info(f"✓ Download successful: {title}")
            logger.info(f"=" * 60)
            
            return DownloadResponse(
                success=True,
                video_id=request.video_id,
                title=title
            )
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Download failed: {error_msg}")
        logger.error(f"=" * 60)
        
        return DownloadResponse(
            success=False,
            video_id=request.video_id,
            error=error_msg
        )


@app.post("/download/file")
async def download_youtube_file(
    request: DownloadRequest,
    x_api_key: str = Header(...)
):
    """
    Download YouTube video audio and return the WAV file.
    
    This endpoint returns the actual audio file for Cloud Run to upload to GCS.
    
    Headers:
        X-API-Key: API key for authentication
    
    Request Body:
        url: YouTube video URL
        video_id: Video ID (for tracking)
    
    Returns:
        WAV file (audio/wav)
    """
    # Verify API key
    verify_api_key(x_api_key)
    
    logger.info(f"=" * 60)
    logger.info(f"File download request: {request.video_id}")
    logger.info(f"URL: {request.url}")
    logger.info(f"=" * 60)
    
    # Create temporary directory (will be cleaned up after response)
    tmpdir = tempfile.mkdtemp()
    
    try:
        # Download and convert audio
        wav_path, title = download_youtube_audio(str(request.url), tmpdir)
        
        logger.info(f"✓ Returning file: {wav_path}")
        logger.info(f"=" * 60)
        
        # Encode title safely for HTTP headers (latin-1 limitation)
        # Use URL encoding for non-ASCII characters
        import urllib.parse
        title_encoded = urllib.parse.quote(title, safe='')
        
        # Return file with cleanup
        return FileResponse(
            path=wav_path,
            media_type="audio/wav",
            filename=f"{request.video_id}.wav",
            headers={
                "X-Video-Title": title_encoded,  # URL-encoded to handle Unicode
                "X-Video-ID": request.video_id
            }
        )
        
    except Exception as e:
        # Clean up temp directory on error
        import shutil
        try:
            shutil.rmtree(tmpdir)
        except:
            pass
        
        error_msg = str(e)
        logger.error(f"❌ Download failed: {error_msg}")
        logger.error(f"=" * 60)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Download failed: {error_msg}"
        )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting YouTube Downloader Service on {host}:{port}")
    logger.info(f"API Key configured: {'Yes' if API_KEY != 'change-me-in-production' else 'No (using default)'}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
