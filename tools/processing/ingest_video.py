"""
Ingest video files: extract audio, transcribe with timestamps, translate, and chunk.
Supports Arabic transcription with translation to English.
Adapted for CENTEF RAG system.
"""
import json
import logging
import os
import sys
import tempfile
from typing import List, Dict, Optional
import re
from pathlib import Path

from google.cloud import storage
from google.cloud import speech_v1 as speech

try:
    from google.cloud import translate_v2 as translate
except ImportError:
    translate = None

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.schemas import Chunk, ChunkMetadata, ChunkAnchor, write_chunks_to_jsonl
from shared.manifest import get_manifest_entry, update_manifest_entry, DocumentStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID", "sylvan-faculty-476113-c9")
SOURCE_BUCKET = os.getenv("SOURCE_BUCKET", "centef-rag-bucket").replace("gs://", "").strip("/")
TARGET_BUCKET = os.getenv("TARGET_BUCKET", "centef-rag-chunks").replace("gs://", "").strip("/")
SOURCE_DATA_PREFIX = os.getenv("SOURCE_DATA_PREFIX", "data").strip("/")


def get_storage_client():
    return storage.Client(project=PROJECT_ID)


def get_speech_client():
    return speech.SpeechClient()


def get_translate_client():
    if translate is None:
        raise RuntimeError("Translation library not available. Install with: pip install google-cloud-translate")
    return translate.Client()


def extract_audio_to_gcs(video_gcs_uri: str, audio_gcs_uri: str) -> str:
    """
    Extract audio from video and save to GCS.
    Note: This requires ffmpeg. For production, you might want to use a Cloud Function
    or Cloud Run job with ffmpeg installed, or use a service like Video Intelligence API.
    
    For now, this is a placeholder - you'll need to handle audio extraction separately
    or upload the audio directly.
    """
    print(f"NOTE: Audio extraction requires external processing.")
    print(f"Please extract audio from {video_gcs_uri} and upload to {audio_gcs_uri}")
    print(f"Or use the audio file directly if available.")
    return audio_gcs_uri


def transcribe_audio_with_timestamps(audio_gcs_uri: str, language_code: str = "ar-SA") -> List[Dict]:
    """
    Transcribe audio with word-level timestamps using Google Speech-to-Text.
    Returns list of segments with timestamps and text.
    """
    logger.info(f"Transcribing audio: {audio_gcs_uri}")
    logger.info(f"Language: {language_code}")

    client = get_speech_client()

    audio = speech.RecognitionAudio(uri=audio_gcs_uri)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code=language_code,
        enable_word_time_offsets=True,
        enable_automatic_punctuation=True,
        model="default",  # or "video" for video content
    )

    # Use long_running_recognize for files > 1 minute
    operation = client.long_running_recognize(config=config, audio=audio)

    logger.info("Waiting for transcription to complete...")
    response = operation.result(timeout=3600)  # 60 minute timeout (for long videos)

    segments = []

    for result in response.results:
        alternative = result.alternatives[0]

        # Get the full transcript for this segment
        transcript = alternative.transcript

        # Get timing from word offsets
        if alternative.words:
            start_time = alternative.words[0].start_time.total_seconds()
            end_time = alternative.words[-1].end_time.total_seconds()
        else:
            # Fallback if no word timings
            start_time = 0.0
            end_time = 0.0

        segments.append({
            'text': transcript,
            'start_sec': start_time,
            'end_sec': end_time,
            'language': language_code
        })

    logger.info(f"Transcribed {len(segments)} segments")
    return segments


def translate_segments(segments: List[Dict], target_language: str = "en") -> List[Dict]:
    """
    Translate text segments to target language.
    Adds translated_text field to each segment.
    """
    logger.info(f"Translating {len(segments)} segments to {target_language}...")

    client = get_translate_client()

    for seg in segments:
        # Translate the text
        result = client.translate(
            seg['text'],
            target_language=target_language,
            source_language=seg.get('language', 'ar')[:2]  # Just language code, not locale
        )

        seg['translated_text'] = result['translatedText']
        seg['detected_source_language'] = result.get('detectedSourceLanguage', '')

    logger.info("Translation complete")
    return segments


def window_segments(segments: List[Dict], window_seconds: float = 30.0) -> List[Dict]:
    """
    Combine segments into time windows similar to SRT processing.
    """
    if not segments:
        return []
    
    windowed = []
    current_window = []
    window_start = segments[0]['start_sec']
    
    for seg in segments:
        # Check if adding this segment would exceed the window
        if current_window and (seg['end_sec'] - window_start) > window_seconds:
            # Finalize current window
            windowed.append({
                'text': ' '.join(s['text'] for s in current_window),
                'translated_text': ' '.join(s.get('translated_text', '') for s in current_window),
                'start_sec': window_start,
                'end_sec': current_window[-1]['end_sec'],
                'language': current_window[0].get('language', ''),
                'segment_count': len(current_window)
            })
            
            # Start new window
            current_window = [seg]
            window_start = seg['start_sec']
        else:
            current_window.append(seg)
    
    # Finalize last window
    if current_window:
        windowed.append({
            'text': ' '.join(s['text'] for s in current_window),
            'translated_text': ' '.join(s.get('translated_text', '') for s in current_window),
            'start_sec': window_start,
            'end_sec': current_window[-1]['end_sec'],
            'language': current_window[0].get('language', ''),
            'segment_count': len(current_window)
        })
    
    return windowed


def segments_to_chunks(segments: List[Dict], source_id: str, source_uri: str, title: str) -> List[Chunk]:
    """Convert windowed segments to CENTEF Chunk objects"""
    chunks = []

    for i, seg in enumerate(segments, 1):
        # Create metadata
        metadata = ChunkMetadata(
            id=f"{source_id}_chunk_{i}",
            source_id=source_id,
            filename=source_uri.split("/")[-1],
            title=title,
            mimetype="video/mp4"
        )

        # Create anchor with video timing information
        anchor = ChunkAnchor(
            start_sec=seg['start_sec'],
            end_sec=seg['end_sec']
        )

        # Create chunk with video-specific content
        # Use translated text if available and non-empty, otherwise use original
        translated = seg.get('translated_text', '').strip()
        original = seg.get('text', '').strip()
        
        if translated:
            content = translated
            # Optionally add original text preview (commented out to avoid truncation)
            # if original and translated != original:
            #     content = f"{content}\n\n[Original: {original[:100]}...]"
        else:
            content = original

        chunk = Chunk(
            metadata=metadata,
            anchor=anchor,
            content=content,
            chunk_index=i
        )
        chunks.append(chunk)

    return chunks


def process_video(video_gcs_uri: str, source_id: str, audio_gcs_uri: Optional[str] = None,
                  language_code: str = "ar-SA", translate_to: str = "en",
                  window_seconds: float = 30.0):
    """
    Process a video: transcribe audio, translate, and create chunks.
    Updates manifest entry with processing status.

    Args:
        video_gcs_uri: GCS URI of the video file
        source_id: Source ID from manifest
        audio_gcs_uri: GCS URI of extracted audio (or None to derive from video URI)
        language_code: Language code for transcription (e.g., "ar-SA" for Arabic)
        translate_to: Target language for translation (e.g., "en" for English)
        window_seconds: Time window for chunking
    """
    logger.info(f"Processing video: {video_gcs_uri}")
    logger.info(f"Source ID: {source_id}")
    logger.info(f"Window size: {window_seconds}s")

    try:
        # Get manifest entry
        entry = get_manifest_entry(source_id)
        if not entry:
            raise ValueError(f"No manifest entry found for source_id: {source_id}")

        # Update status to processing
        update_manifest_entry(source_id, {"status": DocumentStatus.PENDING_PROCESSING})

        # If no audio URI provided, assume audio needs extraction or is provided separately
        if not audio_gcs_uri:
            # For now, user must provide audio separately
            audio_gcs_uri = video_gcs_uri.replace(".mp4", ".wav").replace(".m4a", ".wav")
            logger.info(f"NOTE: Please ensure audio is available at: {audio_gcs_uri}")
            logger.info(f"You can extract audio using ffmpeg:")
            logger.info(f"  ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 output.wav")

        # Transcribe with timestamps
        segments = transcribe_audio_with_timestamps(audio_gcs_uri, language_code)

        if not segments:
            logger.error("No transcription segments generated")
            update_manifest_entry(source_id, {
                "status": DocumentStatus.ERROR,
                "notes": "Failed to generate transcription segments"
            })
            return

        # Translate if target language is different
        if translate_to and translate_to != language_code[:2]:
            segments = translate_segments(segments, translate_to)
        else:
            logger.info(f"Skipping translation (source and target language are the same or no translation requested)")

        # Window the segments
        windowed = window_segments(segments, window_seconds)
        logger.info(f"Created {len(windowed)} time windows from {sum(w['segment_count'] for w in windowed)} segments")

        # Convert to chunks using project schema
        chunks = segments_to_chunks(windowed, source_id, video_gcs_uri, entry.title)

        # Show preview
        if chunks:
            first = chunks[0]
            logger.info(f"First chunk preview:")
            duration = first.anchor.end_sec - first.anchor.start_sec if first.anchor.end_sec and first.anchor.start_sec else 0
            logger.info(f"  Duration: {duration:.1f}s")
            logger.info(f"  Time range: {first.anchor.start_sec:.1f}s - {first.anchor.end_sec:.1f}s")
            logger.info(f"  Content: {first.content[:100]}...")

        # Write chunks to JSONL
        data_path = f"gs://{TARGET_BUCKET}/data/{source_id}.jsonl"
        write_chunks_to_jsonl(chunks, data_path)
        logger.info(f"Uploaded {len(chunks)} chunks to {data_path}")

        # Update manifest with success
        update_manifest_entry(source_id, {
            "status": DocumentStatus.PENDING_SUMMARY,
            "data_path": data_path
        })

        logger.info(f"✓ Video processing complete for {source_id}")

    except Exception as e:
        logger.error(f"Error processing video: {e}", exc_info=True)
        update_manifest_entry(source_id, {
            "status": DocumentStatus.ERROR,
            "notes": f"Processing error: {str(e)}"
        })
        raise


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ingest video with transcription and translation")
    parser.add_argument("source_id", help="Source ID from manifest")
    parser.add_argument("video_uri", help="GCS URI of video file (gs://bucket/path/video.mp4)")
    parser.add_argument("--audio-uri", help="GCS URI of audio file (if extracted separately)")
    parser.add_argument("--language", default="ar-SA", help="Source language code (default: ar-SA)")
    parser.add_argument("--translate", default="en", help="Target language for translation (default: en)")
    parser.add_argument("--window", type=float, default=30.0, help="Time window in seconds (default: 30)")

    args = parser.parse_args()

    process_video(
        video_gcs_uri=args.video_uri,
        source_id=args.source_id,
        audio_gcs_uri=args.audio_uri,
        language_code=args.language,
        translate_to=args.translate,
        window_seconds=args.window
    )


if __name__ == "__main__":
    main()
