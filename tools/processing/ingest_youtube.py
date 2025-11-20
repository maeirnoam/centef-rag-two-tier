"""
Download audio from a YouTube URL with multiple fallback methods:
1. pytubefix (primary method - maintained fork, simpler, may avoid bot detection)
2. yt-dlp (fallback if pytubefix fails)
3. youtube-transcript-api (for videos with existing captions - fastest)

Then calls the existing video ingestion pipeline (transcribe -> translate -> chunk -> upload JSONL).
Adapted for CENTEF RAG system.

Usage example:
python tools/processing/ingest_youtube.py SOURCE_ID "https://www.youtube.com/watch?v=VIDEO_ID" \
  --language ar-SA --translate en --window 30
"""
import os
import re
import sys
import logging
import tempfile
import argparse
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Optional, List, Dict

try:
    import yt_dlp
except Exception:
    yt_dlp = None

try:
    from pytubefix import YouTube
except Exception:
    YouTube = None

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except Exception:
    YouTubeTranscriptApi = None

from google.cloud import storage

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.processing.ingest_video import process_video
from shared.manifest import get_manifest_entry, update_manifest_entry, DocumentStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID", "sylvan-faculty-476113-c9")
SOURCE_BUCKET = os.getenv("SOURCE_BUCKET", "centef-rag-bucket").replace("gs://", "").strip("/")
SOURCE_DATA_PREFIX = os.getenv("SOURCE_DATA_PREFIX", "data").strip("/")


def extract_video_id(youtube_url: str) -> str:
    # Try common patterns
    u = urlparse(youtube_url)
    if u.hostname in ("www.youtube.com", "youtube.com"):
        qs = parse_qs(u.query)
        if "v" in qs:
            return qs["v"][0]
    # youtu.be short link
    if u.hostname == "youtu.be":
        return u.path.lstrip('/')
    # Fallback: last path segment
    return Path(u.path).name


def download_audio_local(youtube_url: str, out_dir: str) -> str:
    """
    Download best audio and convert to mono 16k WAV using yt-dlp + ffmpeg.
    Uses browser cookies if available for authentication.
    Returns local path to the WAV file.
    """
    if yt_dlp is None:
        raise RuntimeError("yt-dlp Python package not available. Please install yt-dlp (pip install yt-dlp).")

    # Enhanced Firefox user agent - matches the browser that exported cookies
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"
    
    logger.info(f"Attempting yt-dlp download with URL: {youtube_url}")
    logger.info(f"Using Firefox User-Agent: {user_agent}")

    # Log environment details for debugging bot detection
    import socket
    import platform
    import random
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        logger.info(f"Environment: hostname={hostname}, local_ip={local_ip}")
        logger.info(f"Platform: {platform.system()} {platform.release()}, Python {platform.python_version()}")
    except Exception as e:
        logger.warning(f"Could not get environment info: {e}")

    # Randomize client order to avoid predictable patterns
    # Sometimes try Android first, sometimes iOS
    if random.random() > 0.5:
        player_clients = ["ios", "android"]
        logger.info("Client order: iOS → Android")
    else:
        player_clients = ["android", "ios"]
        logger.info("Client order: Android → iOS")

    # Check for cookies file from environment
    cookies_file = os.getenv("YOUTUBE_COOKIES_FILE", None)
    
    if cookies_file and os.path.exists(cookies_file):
        logger.info(f"Using cookies file: {cookies_file}")
        file_size = os.path.getsize(cookies_file)
        logger.info(f"Cookies file size: {file_size} bytes")
        
        # Log cookie domains for debugging
        try:
            with open(cookies_file, 'r') as f:
                lines = f.readlines()
                domains = set()
                for line in lines:
                    if not line.startswith('#') and line.strip():
                        parts = line.split('\t')
                        if len(parts) > 0:
                            domains.add(parts[0])
                logger.info(f"Cookie domains: {', '.join(sorted(domains)[:10])}...")  # First 10 domains
        except Exception as e:
            logger.warning(f"Could not parse cookies: {e}")
    else:
        logger.info("No cookies file found - using default clients")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(out_dir, "audio.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            },
            {
                "key": "FFmpegMetadata"
            }
        ],
        # Logging
        "quiet": False,
        "no_warnings": False,
        "verbose": True,
        # Enhanced Firefox headers to match cookie source
        "user_agent": user_agent,
        "http_headers": {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Priority": "u=0, i",
            "TE": "trailers",
        },
        # CRITICAL for Cloud Run: Force iOS client which bypasses bot detection
        # iOS client doesn't require cookies and works from cloud environments
        "extractor_args": {"youtube": {
            "player_client": player_clients,  # Randomized order
            "skip": ["dash", "hls"]  # Skip streaming protocols we don't need
        }},
        "nocheckcertificate": True,
        # Bypass age gate
        "age_limit": None,
        # Bot detection bypass - RANDOMIZED sleep intervals to mimic human behavior
        # YouTube detects predictable patterns, so we randomize timing
        "sleep_interval": 1,  # Minimum sleep
        "max_sleep_interval": 15,  # Maximum sleep (increased for randomness)
        "sleep_interval_requests": 1,  # Minimum between requests
        "sleep_interval_subtitles": 1,
        # Additional randomization via sleep_requests
        "min_sleep_interval": 0.5,  # Add minimum threshold
        # Geo bypass
        "geo_bypass": True,
        "geo_bypass_country": "US",
        # Source address randomization (helps with cloud IPs)
        "source_address": None,  # Let system choose
        # Don't check for yt-dlp updates (can trigger bot detection)
        "no_check_certificate": True,
    }

    # Add cookies if available (helps with web client fallback)
    if cookies_file and os.path.exists(cookies_file):
        ydl_opts["cookiefile"] = cookies_file
        logger.info("✓ Cookies configured for authentication")

    # Log full configuration for debugging
    logger.info("=" * 60)
    logger.info("yt-dlp Configuration Summary:")
    logger.info(f"  Player clients: {ydl_opts['extractor_args']['youtube']['player_client']}")
    logger.info(f"  User-Agent: {ydl_opts['user_agent'][:50]}...")
    logger.info(f"  Cookies: {'Yes' if cookies_file and os.path.exists(cookies_file) else 'No'}")
    logger.info(f"  Sleep intervals: {ydl_opts['sleep_interval']}-{ydl_opts['max_sleep_interval']}s")
    logger.info(f"  Geo bypass: {ydl_opts.get('geo_bypass_country', 'None')}")
    logger.info(f"  HTTP Headers:")
    for key, value in list(ydl_opts['http_headers'].items())[:5]:
        logger.info(f"    {key}: {value[:60]}..." if len(str(value)) > 60 else f"    {key}: {value}")
    logger.info("=" * 60)

    logger.info(f"yt-dlp using player_client: {ydl_opts['extractor_args']['youtube']['player_client']}")

    # Create a custom logger to capture HTTP request details
    class RequestLogger:
        def debug(self, msg):
            if 'Sleeping' in msg or 'fake IP' in msg or 'X-Forwarded-For' in msg:
                logger.info(f"[yt-dlp] {msg}")
        def info(self, msg):
            logger.info(f"[yt-dlp] {msg}")
        def warning(self, msg):
            logger.warning(f"[yt-dlp] {msg}")
        def error(self, msg):
            logger.error(f"[yt-dlp] {msg}")

    # Add custom logger to capture more details
    if 'logger' not in ydl_opts:
        ydl_opts['logger'] = RequestLogger()

    try:
        logger.info("=" * 60)
        logger.info("Starting YouTube download...")
        logger.info("=" * 60)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("Starting video info extraction...")
            info = ydl.extract_info(youtube_url, download=True)
            logger.info(f"✓ Successfully extracted: {info.get('title', 'Unknown title')}")
            
            # Log which client was actually used
            if 'protocol' in info:
                logger.info(f"Protocol used: {info.get('protocol')}")
            if 'format_note' in info:
                logger.info(f"Format: {info.get('format_note')}")
            logger.info(f"Video ID: {info.get('id', 'unknown')}")
            
    except Exception as e:
        logger.error("=" * 60)
        logger.error("DOWNLOAD FAILED - Error Details:")
        logger.error("=" * 60)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {e}")
        
        # Check if it's a bot detection error
        error_str = str(e).lower()
        if 'bot' in error_str or 'sign in' in error_str:
            logger.error("⚠ BOT DETECTION ERROR DETECTED!")
            logger.error("This suggests YouTube is blocking the request as automated.")
            logger.error("Possible causes:")
            logger.error("  - Cloud provider IP detected (Google Cloud, AWS, Azure)")
            logger.error("  - User-Agent not matching actual client")
            logger.error("  - Missing or invalid cookies")
            logger.error("  - Request pattern looks automated")
        
        logger.error("=" * 60)
        logger.error(f"Full error details:", exc_info=True)
        raise RuntimeError(f"yt-dlp failed to download: {e}") from e
    
    # find the downloaded wav path
    # yt-dlp uses extension 'wav' after postprocessing
    wav_path = None
    for ext in ("wav", "m4a", "mp3", "webm", "opus"):
        candidate = os.path.join(out_dir, f"audio.{ext}")
        if os.path.exists(candidate):
            wav_path = candidate
            break

    if not wav_path:
        raise RuntimeError("Failed to find downloaded audio file")

    # If not wav, convert to 16k mono wav with ffmpeg
    if not wav_path.lower().endswith('.wav'):
        final_wav = os.path.join(out_dir, "audio.wav")
        cmd = [
            "ffmpeg", "-y", "-i", wav_path,
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            final_wav
        ]
        import subprocess
        subprocess.run(cmd, check=True)
        wav_path = final_wav
    else:
        # Ensure sample rate/channels - re-encode to 16k mono wav to be safe
        reencoded = os.path.join(out_dir, "audio_16k_mono.wav")
        import subprocess
        cmd = [
            "ffmpeg", "-y", "-i", wav_path,
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            reencoded
        ]
        subprocess.run(cmd, check=True)
        wav_path = reencoded

    return wav_path


def download_audio_pytube(youtube_url: str, out_dir: str) -> str:
    """
    Download audio using pytubefix library (maintained fork of pytube).
    Returns local path to the WAV file.
    """
    if YouTube is None:
        raise RuntimeError("pytubefix not available. Install with: pip install pytubefix")

    logger.info("Trying pytubefix download method...")

    try:
        yt = YouTube(youtube_url)

        # Get audio stream
        audio_stream = yt.streams.filter(only_audio=True).first()

        if not audio_stream:
            raise RuntimeError("No audio stream available")

        # Download audio
        logger.info(f"Downloading audio: {yt.title}")
        audio_file = audio_stream.download(output_path=out_dir, filename="audio_raw")

        # Convert to 16k mono WAV with ffmpeg
        wav_path = os.path.join(out_dir, "audio.wav")
        import subprocess
        cmd = [
            "ffmpeg", "-y", "-i", audio_file,
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            wav_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        logger.info(f"✓ pytubefix download successful: {wav_path}")
        return wav_path

    except Exception as e:
        logger.error(f"pytubefix download failed: {e}")
        raise


def try_get_youtube_captions(youtube_url: str, language_code: str = "ar") -> Optional[List[Dict]]:
    """
    Try to get existing YouTube captions using youtube-transcript-api.
    Returns list of caption segments if available, None otherwise.
    This is the fastest method if captions exist!
    """
    if YouTubeTranscriptApi is None:
        logger.warning("youtube-transcript-api not available. Install with: pip install youtube-transcript-api")
        return None

    try:
        video_id = extract_video_id(youtube_url)
        logger.info(f"Checking for existing YouTube captions (language: {language_code})...")

        # Try to get transcript in requested language
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try exact language match first
        try:
            transcript = transcript_list.find_transcript([language_code])
            captions = transcript.fetch()
            logger.info(f"✓ Found {len(captions)} caption segments in {language_code}!")

            # Convert to our format
            segments = []
            for cap in captions:
                segments.append({
                    'text': cap['text'],
                    'start_sec': cap['start'],
                    'end_sec': cap['start'] + cap['duration'],
                    'language': language_code
                })

            return segments

        except Exception:
            # Try auto-generated captions
            logger.info(f"No manual captions in {language_code}, trying auto-generated...")
            try:
                transcript = transcript_list.find_generated_transcript([language_code])
                captions = transcript.fetch()
                logger.info(f"✓ Found {len(captions)} auto-generated caption segments!")

                segments = []
                for cap in captions:
                    segments.append({
                        'text': cap['text'],
                        'start_sec': cap['start'],
                        'end_sec': cap['start'] + cap['duration'],
                        'language': language_code
                    })

                return segments
            except Exception:
                pass

        logger.info("No captions found in requested language")
        return None

    except Exception as e:
        logger.warning(f"Could not fetch captions: {e}")
        return None


def download_audio_with_fallback(youtube_url: str, out_dir: str) -> str:
    """
    Download audio with multiple fallback methods:
    1. Try pytubefix (primary - simpler, maintained fork, may avoid bot detection)
    2. Try yt-dlp (fallback)

    Returns local path to WAV file.
    """
    errors = []

    # Method 1: pytubefix (primary)
    if YouTube is not None:
        try:
            logger.info("Attempting download with pytubefix (method 1/2)...")
            return download_audio_pytube(youtube_url, out_dir)
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"pytubefix failed: {error_msg}")
            errors.append(f"pytubefix: {error_msg}")
    else:
        logger.warning("pytubefix not available, skipping...")
        errors.append("pytubefix: not installed")

    # Method 2: yt-dlp (fallback)
    if yt_dlp is not None:
        try:
            logger.info("Attempting download with yt-dlp (method 2/2)...")
            return download_audio_local(youtube_url, out_dir)
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"yt-dlp failed: {error_msg}")
            errors.append(f"yt-dlp: {error_msg}")
    else:
        logger.warning("yt-dlp not available, skipping...")
        errors.append("yt-dlp: not installed")

    # All methods failed
    error_summary = "All download methods failed:\n" + "\n".join(f"  - {err}" for err in errors)
    raise RuntimeError(error_summary)


def upload_to_gcs(local_path: str, bucket_name: str, dest_path: str) -> str:
    """Upload file to GCS"""
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest_path)
    blob.upload_from_filename(local_path, timeout=1800)
    logger.info(f"Uploaded to gs://{bucket_name}/{dest_path}")
    return f"gs://{bucket_name}/{dest_path}"


def main():
    parser = argparse.ArgumentParser(description="Ingest a YouTube link: download audio, upload to GCS, transcribe+chunk")
    parser.add_argument("source_id", help="Source ID from manifest")
    parser.add_argument("url", help="YouTube URL to ingest")
    parser.add_argument("--bucket", help="GCS bucket to upload audio (default SOURCE_BUCKET)", default=SOURCE_BUCKET)
    parser.add_argument("--prefix", help="Destination prefix in bucket (default data)", default=SOURCE_DATA_PREFIX)
    parser.add_argument("--language", default="en", help="Source language code for STT (default: ar-SA)")
    parser.add_argument("--translate", default="en", help="Target translation language (default: en). Use 'none' to skip translation.")
    parser.add_argument("--window", type=float, default=30.0, help="Chunk window seconds (default 30)")
    args = parser.parse_args()

    try:
        # Get manifest entry
        entry = get_manifest_entry(args.source_id)
        if not entry:
            raise ValueError(f"No manifest entry found for source_id: {args.source_id}")

        # Update status
        update_manifest_entry(args.source_id, {"status": DocumentStatus.PENDING_PROCESSING})

        # Check if captions are available (fastest method!)
        caption_lang = args.language[:2]  # Convert "ar-SA" to "ar"
        captions = try_get_youtube_captions(args.url, caption_lang)

        if captions:
            # We have captions! Skip audio download and use captions directly
            logger.info("✓ Using existing YouTube captions - skipping audio download!")

            from tools.processing.ingest_video import translate_segments, window_segments, segments_to_chunks
            from shared.schemas import write_chunks_to_jsonl

            # Translate if needed
            translate_target = None if args.translate.lower() in ('none', '') else args.translate
            if translate_target and translate_target != caption_lang:
                captions = translate_segments(captions, translate_target)

            # Window the segments
            windowed = window_segments(captions, args.window)
            logger.info(f"Created {len(windowed)} time windows from {len(captions)} caption segments")

            # Convert to chunks
            chunks = segments_to_chunks(windowed, args.source_id, args.url, entry.title)

            # Write chunks to JSONL
            TARGET_BUCKET = os.getenv("TARGET_BUCKET", "centef-rag-chunks").replace("gs://", "").strip("/")
            data_path = f"gs://{TARGET_BUCKET}/data/{args.source_id}.jsonl"
            write_chunks_to_jsonl(chunks, data_path)
            logger.info(f"Uploaded {len(chunks)} chunks to {data_path}")

            # Update manifest with success
            update_manifest_entry(args.source_id, {
                "status": DocumentStatus.PENDING_SUMMARY,
                "data_path": data_path
            })

            logger.info(f"✓ YouTube caption ingestion complete for {args.source_id}")

        else:
            # No captions - download audio and transcribe
            logger.info("No captions available - downloading audio for transcription...")

            with tempfile.TemporaryDirectory() as tmpdir:
                logger.info(f"Downloading audio for: {args.url}")
                wav_local = download_audio_with_fallback(args.url, tmpdir)
                logger.info(f"Audio downloaded: {wav_local}")

                vid_id = extract_video_id(args.url)
                dest_blob = f"{args.prefix}/youtube_{vid_id}.wav"
                logger.info(f"Uploading to gs://{args.bucket}/{dest_blob} ...")
                audio_gs = upload_to_gcs(wav_local, args.bucket, dest_blob)

                # Create a pseudo video URI for provenance
                video_uri = args.url  # Keep the original YouTube URL

                # Call process_video
                translate_target = None if args.translate.lower() in ('none', '') else args.translate
                process_video(
                    video_gcs_uri=video_uri,
                    source_id=args.source_id,
                    audio_gcs_uri=audio_gs,
                    language_code=args.language,
                    translate_to=translate_target,
                    window_seconds=args.window
                )

                logger.info(f"✓ YouTube video ingestion complete for {args.source_id}")

    except Exception as e:
        logger.error(f"Error processing YouTube video: {e}", exc_info=True)
        update_manifest_entry(args.source_id, {
            "status": DocumentStatus.ERROR,
            "notes": f"YouTube ingestion error: {str(e)}"
        })
        raise

if __name__ == '__main__':
    main()
