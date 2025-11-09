"""
Batch processing script for ingesting multiple PDFs through the full pipeline.
Processes PDFs: upload -> extract chunks -> summarize -> approve -> index
"""
import os
import sys
import time
import logging
from pathlib import Path
from typing import List
import re

from google.cloud import storage
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import ManifestEntry, create_manifest_entry, update_manifest_entry
from tools.processing.process_pdf import process_pdf
from tools.processing.summarize_chunks import summarize_chunks
from services.embedding.index_documents import index_document

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

SOURCE_BUCKET = os.getenv("SOURCE_BUCKET", "centef-rag-bucket")


def clean_filename(filename: str) -> str:
    """Clean filename for use as source_id."""
    # Remove extension
    name = Path(filename).stem
    # Replace spaces and special characters with hyphens
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '-', name)
    return name.lower().strip('-')


def upload_to_gcs(local_path: str, gcs_filename: str) -> str:
    """
    Upload file to GCS bucket.
    
    Args:
        local_path: Local file path
        gcs_filename: Filename to use in GCS
    
    Returns:
        GCS URI
    """
    client = storage.Client()
    bucket = client.bucket(SOURCE_BUCKET)
    blob = bucket.blob(f"sources/{gcs_filename}")
    
    logger.info(f"Uploading {local_path} to gs://{SOURCE_BUCKET}/sources/{gcs_filename}")
    blob.upload_from_filename(local_path)
    
    return f"gs://{SOURCE_BUCKET}/sources/{gcs_filename}"


def process_single_pdf(pdf_path: str, skip_if_exists: bool = True) -> bool:
    """
    Process a single PDF through the full pipeline.
    
    Args:
        pdf_path: Path to PDF file
        skip_if_exists: Skip if document already exists in manifest
    
    Returns:
        True if successful, False otherwise
    """
    try:
        filename = Path(pdf_path).name
        source_id = clean_filename(filename)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing: {filename}")
        logger.info(f"Source ID: {source_id}")
        logger.info(f"{'='*80}\n")
        
        # Check if already exists
        if skip_if_exists:
            from shared.manifest import get_manifest_entry
            existing = get_manifest_entry(source_id)
            if existing:
                logger.info(f"Document {source_id} already exists with status {existing.status}. Skipping.")
                return True
        
        # 1. Upload to GCS
        gcs_uri = upload_to_gcs(pdf_path, filename)
        logger.info(f"✓ Uploaded to {gcs_uri}")
        
        # 2. Create manifest entry
        entry = ManifestEntry(
            source_id=source_id,
            filename=filename,
            title=Path(filename).stem,
            mimetype="application/pdf",
            source_uri=gcs_uri
        )
        create_manifest_entry(entry)
        logger.info(f"✓ Created manifest entry")
        
        # 3. Process PDF (extract chunks)
        logger.info(f"Processing PDF...")
        process_pdf(source_id, gcs_uri)
        logger.info(f"✓ Extracted chunks")
        
        # 4. Generate summary
        logger.info(f"Generating summary with Gemini...")
        summarize_chunks(source_id)
        logger.info(f"✓ Generated summary")
        
        # 5. Approve document
        logger.info(f"Approving document...")
        update_manifest_entry(source_id, {
            'approved': True,
            'status': 'pending_embedding'
        })
        logger.info(f"✓ Approved")
        
        # 6. Index to Discovery Engine
        logger.info(f"Indexing to Discovery Engine...")
        from shared.manifest import get_manifest_entry as get_entry
        entry = get_entry(source_id)
        index_document(entry)
        logger.info(f"✓ Indexed")
        
        logger.info(f"\n✓✓✓ Successfully processed {filename} ✓✓✓\n")
        return True
        
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {e}", exc_info=True)
        return False


def batch_process_directory(directory: str, skip_if_exists: bool = True):
    """
    Process all PDFs in a directory.
    
    Args:
        directory: Path to directory containing PDFs
        skip_if_exists: Skip documents that already exist
    """
    pdf_files = list(Path(directory).glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {directory}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    successful = 0
    failed = 0
    skipped = 0
    
    for i, pdf_path in enumerate(pdf_files, 1):
        logger.info(f"\n{'#'*80}")
        logger.info(f"Processing file {i}/{len(pdf_files)}")
        logger.info(f"{'#'*80}")
        
        # Check if exists and should skip
        if skip_if_exists:
            source_id = clean_filename(pdf_path.name)
            from shared.manifest import get_manifest_entry
            existing = get_manifest_entry(source_id)
            if existing:
                logger.info(f"Skipping {pdf_path.name} (already exists with status: {existing.status})")
                skipped += 1
                continue
        
        success = process_single_pdf(str(pdf_path), skip_if_exists=skip_if_exists)
        
        if success:
            successful += 1
        else:
            failed += 1
        
        # Small delay between documents
        if i < len(pdf_files):
            time.sleep(2)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Batch Processing Complete!")
    logger.info(f"Total: {len(pdf_files)} | Successful: {successful} | Failed: {failed} | Skipped: {skipped}")
    logger.info(f"{'='*80}\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch process PDFs through the full pipeline")
    parser.add_argument("--directory", required=True, help="Directory containing PDF files")
    parser.add_argument("--no-skip", action="store_true", help="Process even if document already exists")
    
    args = parser.parse_args()
    
    if not Path(args.directory).exists():
        logger.error(f"Directory not found: {args.directory}")
        return 1
    
    batch_process_directory(args.directory, skip_if_exists=not args.no_skip)
    return 0


if __name__ == "__main__":
    sys.exit(main())
