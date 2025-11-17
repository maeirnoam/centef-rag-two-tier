"""
Client for external YouTube downloader service.
Used by Cloud Run to download YouTube videos from non-cloud IPs.
"""
import os
import logging
import tempfile
from typing import Optional, Tuple
import requests

logger = logging.getLogger(__name__)


def _get_config():
    """Get configuration from environment variables (read dynamically)"""
    return {
        'url': os.getenv("YOUTUBE_DOWNLOADER_URL", ""),
        'api_key': os.getenv("YOUTUBE_DOWNLOADER_API_KEY", ""),
        'timeout': int(os.getenv("YOUTUBE_DOWNLOADER_TIMEOUT", "300"))
    }


class YouTubeDownloaderError(Exception):
    """Exception raised when external downloader fails"""
    pass


def is_external_downloader_configured() -> bool:
    """Check if external YouTube downloader is configured"""
    config = _get_config()
    return bool(config['url'] and config['api_key'])


def download_youtube_via_external_service(youtube_url: str, video_id: str) -> Tuple[str, str]:
    """
    Download YouTube video audio via external service.
    
    Args:
        youtube_url: YouTube video URL
        video_id: YouTube video ID
        
    Returns:
        Tuple of (local_wav_path, video_title)
        
    Raises:
        YouTubeDownloaderError: If download fails
    """
    if not is_external_downloader_configured():
        raise YouTubeDownloaderError(
            "External YouTube downloader not configured. "
            "Set YOUTUBE_DOWNLOADER_URL and YOUTUBE_DOWNLOADER_API_KEY environment variables."
        )
    
    config = _get_config()
    
    logger.info(f"Requesting download from external service: {youtube_url}")
    logger.info(f"External service URL: {config['url']}")
    
    # Prepare request
    endpoint = f"{config['url'].rstrip('/')}/download/file"
    headers = {
        "X-API-Key": config['api_key'],
        "Content-Type": "application/json"
    }
    payload = {
        "url": youtube_url,
        "video_id": video_id
    }
    
    try:
        # Make request to external service
        logger.info(f"POST {endpoint}")
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=config['timeout'],
            stream=True  # Stream large files
        )
        
        # Check response
        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"External downloader returned {response.status_code}: {error_detail}")
            raise YouTubeDownloaderError(
                f"External downloader failed with status {response.status_code}: {error_detail}"
            )
        
        # Get video title from headers (URL-encoded to handle Unicode)
        import urllib.parse
        video_title_encoded = response.headers.get("X-Video-Title", f"YouTube Video {video_id}")
        video_title = urllib.parse.unquote(video_title_encoded)
        logger.info(f"Video title: {video_title}")
        
        # Save to temporary file
        tmpdir = tempfile.mkdtemp()
        wav_path = os.path.join(tmpdir, f"{video_id}.wav")
        
        logger.info(f"Downloading audio file to: {wav_path}")
        
        # Stream download to file
        total_bytes = 0
        with open(wav_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_bytes += len(chunk)
        
        file_size_mb = total_bytes / 1024 / 1024
        logger.info(f"✓ Downloaded {file_size_mb:.2f} MB to {wav_path}")
        
        return wav_path, video_title
        
    except requests.exceptions.Timeout:
        logger.error(f"External downloader timeout after {config['timeout']}s")
        raise YouTubeDownloaderError(
            f"External downloader timeout after {config['timeout']} seconds. "
            "Video may be too long or service is overloaded."
        )
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Cannot connect to external downloader: {e}")
        raise YouTubeDownloaderError(
            f"Cannot connect to external YouTube downloader at {config['url']}. "
            "Check if service is running and URL is correct."
        )
        
    except Exception as e:
        logger.error(f"Unexpected error calling external downloader: {e}", exc_info=True)
        raise YouTubeDownloaderError(f"Failed to download via external service: {e}")


def health_check_external_service() -> dict:
    """
    Check health of external YouTube downloader service.
    
    Returns:
        Dict with status information
    """
    if not is_external_downloader_configured():
        return {
            "configured": False,
            "status": "not_configured",
            "message": "YOUTUBE_DOWNLOADER_URL or YOUTUBE_DOWNLOADER_API_KEY not set"
        }
    
    config = _get_config()
    
    try:
        endpoint = f"{config['url'].rstrip('/')}/health"
        response = requests.get(endpoint, timeout=10)
        
        if response.status_code == 200:
            health_data = response.json()
            return {
                "configured": True,
                "status": "healthy",
                "url": config['url'],
                "details": health_data
            }
        else:
            return {
                "configured": True,
                "status": "unhealthy",
                "url": config['url'],
                "status_code": response.status_code
            }
            
    except Exception as e:
        return {
            "configured": True,
            "status": "unreachable",
            "url": config['url'],
            "error": str(e)
        }
