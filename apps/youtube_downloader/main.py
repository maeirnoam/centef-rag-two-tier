"""
YouTube Downloader Service - External API
Runs on hstgr (non-cloud IP) to bypass YouTube bot detection.

This service:
1. Receives YouTube URL from Cloud Run
2. Downloads audio using pytubefix
3. Returns the audio file to Cloud Run

No GCS credentials needed - Cloud Run handles storage.
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

# Import download functions (simplified - no GCS dependencies)
try:
    from pytubefix import YouTube
except ImportError:
    YouTube = None
    logger.warning("pytubefix not installed")


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


def verify_api_key(x_api_key: str = Header(...)) -> bool:
    """Verify API key from request header"""
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return True


def download_youtube_audio(youtube_url: str, out_dir: str) -> tuple[str, str]:
    """
    Download YouTube audio using pytubefix.
    Returns: (wav_path, video_title)
    """
    if YouTube is None:
        raise RuntimeError("pytubefix not available. Install with: pip install pytubefix")

    logger.info(f"Starting download: {youtube_url}")
    
    try:
        yt = YouTube(str(youtube_url))
        title = yt.title
        logger.info(f"Video title: {title}")

        # Get audio stream
        audio_stream = yt.streams.filter(only_audio=True).first()
        if not audio_stream:
            raise RuntimeError("No audio stream available")

        # Download audio
        logger.info(f"Downloading audio stream...")
        audio_file = audio_stream.download(output_path=out_dir, filename="audio_raw")
        logger.info(f"Download complete: {audio_file}")

        # Convert to 16kHz mono WAV with ffmpeg
        wav_path = os.path.join(out_dir, "audio.wav")
        import subprocess
        
        cmd = [
            "ffmpeg", "-y", "-i", audio_file,
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
        "pytubefix_available": YouTube is not None
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "pytubefix": "available" if YouTube is not None else "missing",
        "ffmpeg": "available"  # TODO: Check ffmpeg availability
    }


@app.post("/download", response_model=DownloadResponse)
async def download_youtube(
    request: DownloadRequest,
    authorized: bool = Header(alias="X-API-Key", default=None)
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
    verify_api_key(authorized)
    
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
