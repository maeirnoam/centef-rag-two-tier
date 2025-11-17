"""
Ingest standalone audio files: transcribe with timestamps, translate, and chunk.
Supports Arabic transcription with translation to English.
Adapted for CENTEF RAG system.

Usage example:
python tools/processing/ingest_audio.py SOURCE_ID gs://bucket/audio.wav \
  --language ar-SA --translate en --window 30
"""
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.processing.ingest_video import (
    transcribe_audio_with_timestamps,
    translate_segments,
    window_segments,
    segments_to_chunks
)
from shared.schemas import write_chunks_to_jsonl
from shared.manifest import get_manifest_entry, update_manifest_entry, DocumentStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID", "sylvan-faculty-476113-c9")
TARGET_BUCKET = os.getenv("TARGET_BUCKET", "centef-rag-chunks").replace("gs://", "").strip("/")


def process_audio(audio_gcs_uri: str, source_id: str,
                  language_code: str = "ar-SA", translate_to: str = "en",
                  window_seconds: float = 30.0):
    """
    Process an audio file: transcribe, translate, and create chunks.
    Updates manifest entry with processing status.

    Args:
        audio_gcs_uri: GCS URI of the audio file
        source_id: Source ID from manifest
        language_code: Language code for transcription (e.g., "ar-SA" for Arabic)
        translate_to: Target language for translation (e.g., "en" for English)
        window_seconds: Time window for chunking
    """
    logger.info(f"Processing audio: {audio_gcs_uri}")
    logger.info(f"Source ID: {source_id}")
    logger.info(f"Window size: {window_seconds}s")

    try:
        # Get manifest entry
        entry = get_manifest_entry(source_id)
        if not entry:
            raise ValueError(f"No manifest entry found for source_id: {source_id}")

        # Update status to processing
        update_manifest_entry(source_id, {"status": DocumentStatus.PENDING_PROCESSING})

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

        # Window the segments
        windowed = window_segments(segments, window_seconds)
        logger.info(f"Created {len(windowed)} time windows from {sum(w['segment_count'] for w in windowed)} segments")

        # Convert to chunks using project schema
        chunks = segments_to_chunks(windowed, source_id, audio_gcs_uri, entry.title)

        # Show preview
        if chunks:
            first = chunks[0]
            logger.info(f"First chunk preview:")
            logger.info(f"  Duration: {first.chunk_data['duration_sec']:.1f}s")
            logger.info(f"  Original: {first.chunk_data['text_original'][:100]}...")
            logger.info(f"  Translated: {first.content[:100]}...")

        # Write chunks to JSONL
        data_path = f"gs://{TARGET_BUCKET}/data/{source_id}.jsonl"
        write_chunks_to_jsonl(chunks, data_path)
        logger.info(f"Uploaded {len(chunks)} chunks to {data_path}")

        # Update manifest with success
        update_manifest_entry(source_id, {
            "status": DocumentStatus.PENDING_SUMMARY,
            "data_path": data_path
        })

        logger.info(f"✓ Audio processing complete for {source_id}")

    except Exception as e:
        logger.error(f"Error processing audio: {e}", exc_info=True)
        update_manifest_entry(source_id, {
            "status": DocumentStatus.ERROR,
            "notes": f"Processing error: {str(e)}"
        })
        raise


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ingest audio with transcription and translation")
    parser.add_argument("source_id", help="Source ID from manifest")
    parser.add_argument("audio_uri", help="GCS URI of audio file (gs://bucket/path/audio.wav)")
    parser.add_argument("--language", default="ar-SA", help="Source language code (default: ar-SA)")
    parser.add_argument("--translate", default="en", help="Target language for translation (default: en)")
    parser.add_argument("--window", type=float, default=30.0, help="Time window in seconds (default: 30)")

    args = parser.parse_args()

    process_audio(
        audio_gcs_uri=args.audio_uri,
        source_id=args.source_id,
        language_code=args.language,
        translate_to=args.translate,
        window_seconds=args.window
    )


if __name__ == "__main__":
    main()