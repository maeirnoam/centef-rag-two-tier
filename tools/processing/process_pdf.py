"""
PDF processing tool for CENTEF RAG system.
Chunks PDFs into page-based chunks using PyMuPDF and writes to GCS.
"""
import argparse
import logging
import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import List

import fitz  # PyMuPDF

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


def download_from_gcs(gcs_path: str, local_path: str) -> str:
    """
    Download file from GCS if needed.
    
    Args:
        gcs_path: GCS path (gs://bucket/path) or local path
        local_path: Where to save locally
    
    Returns:
        Local file path
    """
    if not gcs_path.startswith("gs://"):
        return gcs_path
    
    logger.info(f"Downloading {gcs_path} to {local_path}")
    
    # Parse GCS path
    parts = gcs_path.replace("gs://", "").split("/", 1)
    bucket_name = parts[0]
    blob_path = parts[1]
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.download_to_filename(local_path)
    
    return local_path


def extract_pdf_text_by_page(pdf_path: str) -> List[tuple[int, str]]:
    """
    Extract text from PDF using PyMuPDF, organized by page.
    
    Args:
        pdf_path: Path to PDF file (local or GCS)
    
    Returns:
        List of tuples (page_number, text_content)
    """
    logger.info(f"Extracting text from PDF: {pdf_path}")
    
    # Download from GCS if needed
    if pdf_path.startswith("gs://"):
        local_path = f"/tmp/{os.path.basename(pdf_path)}"
        pdf_path = download_from_gcs(pdf_path, local_path)
    
    pages = []
    
    try:
        # Open PDF with PyMuPDF
        doc = fitz.open(pdf_path)
        
        logger.info(f"PDF has {len(doc)} pages")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract text from page
            text = page.get_text("text")
            
            # Clean up text
            text = text.strip()
            
            if text:  # Only include pages with content
                pages.append((page_num + 1, text))  # Page numbers are 1-indexed
            else:
                logger.warning(f"Page {page_num + 1} has no text content")
        
        doc.close()
        
        logger.info(f"Extracted text from {len(pages)} pages")
        
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}", exc_info=True)
        raise
    
    return pages


def process_pdf(source_id: str, input_path: str) -> str:
    """
    Process a PDF file into page-based chunks.
    
    Args:
        source_id: The source_id from manifest
        input_path: Path to PDF file (local or GCS)
    
    Returns:
        Path to output JSONL file in GCS
    """
    logger.info(f"Processing PDF for source_id={source_id}, input={input_path}")
    
    # Get manifest entry
    entry = get_manifest_entry(source_id)
    if not entry:
        raise ValueError(f"Manifest entry not found for source_id={source_id}")
    
    # Extract pages
    pages = extract_pdf_text_by_page(input_path)
    
    # Create chunks
    chunks = []
    for page_num, text in pages:
        chunk_id = f"{source_id}_page_{page_num}"
        
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
        
        anchor = ChunkAnchor(page=page_num)
        
        chunk = Chunk(
            metadata=metadata,
            anchor=anchor,
            content=text,
            chunk_index=page_num - 1
        )
        
        chunks.append(chunk)
    
    logger.info(f"Created {len(chunks)} page-based chunks")
    
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
    parser = argparse.ArgumentParser(description="Process PDF into chunks")
    parser.add_argument("--source-id", required=True, help="Source ID from manifest")
    parser.add_argument("--input", required=True, help="Path to input PDF file")
    
    args = parser.parse_args()
    
    try:
        output_path = process_pdf(args.source_id, args.input)
        print(f"Successfully processed PDF. Output: {output_path}")
        return 0
    except Exception as e:
        logger.error(f"Error processing PDF: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
