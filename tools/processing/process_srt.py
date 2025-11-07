"""
SRT (subtitle) processing tool for CENTEF RAG system.
Chunks SRT files by timestamp segments and writes to GCS.
"""
import argparse
import logging
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

from google.cloud import storage

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
PROJECT_ID = os.getenv("PROJECT_ID")
TARGET_BUCKET = os.getenv("TARGET_BUCKET", "centef-rag-chunks")


def parse_srt_timestamp(timestamp: str) -> float:
    """
    Parse SRT timestamp to seconds.
    
    Args:
        timestamp: SRT timestamp (e.g., "00:01:23,456")
    
    Returns:
        Time in seconds
    """
    # Format: HH:MM:SS,mmm
    match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', timestamp)
    if not match:
        raise ValueError(f"Invalid SRT timestamp: {timestamp}")
    
    hours, minutes, seconds, milliseconds = match.groups()
    total_seconds = (
        int(hours) * 3600 +
        int(minutes) * 60 +
        int(seconds) +
        int(milliseconds) / 1000
    )
    
    return total_seconds


def parse_srt_file(srt_path: str) -> List[Tuple[float, float, str]]:
    """
    Parse SRT file into segments.
    
    Args:
        srt_path: Path to SRT file
    
    Returns:
        List of tuples (start_sec, end_sec, text)
    """
    logger.info(f"Parsing SRT file: {srt_path}")
    
    segments = []
    
    # TODO: Handle GCS paths
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by double newline (segment separator)
    raw_segments = re.split(r'\n\s*\n', content.strip())
    
    for raw_segment in raw_segments:
        lines = raw_segment.strip().split('\n')
        
        if len(lines) < 3:
            continue
        
        # First line is the sequence number (ignore)
        # Second line is the timestamp
        timestamp_line = lines[1]
        
        # Parse timestamps: "00:01:23,456 --> 00:01:26,789"
        match = re.match(r'(.+?)\s*-->\s*(.+)', timestamp_line)
        if not match:
            logger.warning(f"Could not parse timestamp line: {timestamp_line}")
            continue
        
        start_str, end_str = match.groups()
        start_sec = parse_srt_timestamp(start_str.strip())
        end_sec = parse_srt_timestamp(end_str.strip())
        
        # Remaining lines are the text
        text = '\n'.join(lines[2:])
        
        segments.append((start_sec, end_sec, text))
    
    logger.info(f"Parsed {len(segments)} segments from SRT")
    return segments


def process_srt(source_id: str, input_path: str) -> str:
    """
    Process an SRT file into timestamp-based chunks.
    
    Args:
        source_id: The source_id from manifest
        input_path: Path to SRT file (local or GCS)
    
    Returns:
        Path to output JSONL file in GCS
    """
    logger.info(f"Processing SRT for source_id={source_id}, input={input_path}")
    
    # Get manifest entry
    entry = get_manifest_entry(source_id)
    if not entry:
        raise ValueError(f"Manifest entry not found for source_id={source_id}")
    
    # Parse SRT segments
    segments = parse_srt_file(input_path)
    
    # Create chunks
    chunks = []
    for i, (start_sec, end_sec, text) in enumerate(segments):
        chunk_id = f"{source_id}_seg_{i}"
        
        metadata = ChunkMetadata(
            id=chunk_id,
            source_id=source_id,
            filename=entry.filename,
            title=entry.title,
            mimetype=entry.mimetype,
            author=entry.author,
            organization=entry.organization,
            date=entry.date,
            publisher=entry.publisher,
            tags=entry.tags
        )
        
        anchor = ChunkAnchor(start_sec=start_sec, end_sec=end_sec)
        
        chunk = Chunk(
            metadata=metadata,
            anchor=anchor,
            content=text,
            chunk_index=i
        )
        
        chunks.append(chunk)
    
    logger.info(f"Created {len(chunks)} timestamp-based chunks")
    
    # Write to GCS
    output_path = f"gs://{TARGET_BUCKET}/data/{source_id}.jsonl"
    
    # Write locally then upload
    local_output = f"/tmp/{source_id}.jsonl"
    write_chunks_to_jsonl(chunks, local_output)
    
    # Upload to GCS
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(TARGET_BUCKET.replace("gs://", ""))
    blob = bucket.blob(f"data/{source_id}.jsonl")
    blob.upload_from_filename(local_output)
    
    logger.info(f"Uploaded chunks to {output_path}")
    
    # Update manifest status
    update_manifest_entry(source_id, {
        "status": DocumentStatus.PENDING_SUMMARY,
        "data_path": output_path
    })
    
    logger.info(f"Updated manifest status to {DocumentStatus.PENDING_SUMMARY}")
    
    return output_path


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Process SRT into chunks")
    parser.add_argument("--source-id", required=True, help="Source ID from manifest")
    parser.add_argument("--input", required=True, help="Path to input SRT file")
    
    args = parser.parse_args()
    
    try:
        output_path = process_srt(args.source_id, args.input)
        print(f"Successfully processed SRT. Output: {output_path}")
        return 0
    except Exception as e:
        logger.error(f"Error processing SRT: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
