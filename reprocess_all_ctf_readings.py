"""
Reprocess all files (PDF and DOCX) from CTF Essential Readings directory.
This will process new files and reprocess existing ones with improved summarization.
"""
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List
import re

sys.path.insert(0, str(Path(__file__).parent))

from google.cloud import storage
from shared.manifest import get_manifest_entry, create_manifest_entry, update_manifest_entry, ManifestEntry, DocumentStatus
from tools.processing.process_pdf import process_pdf
from tools.processing.process_docx import process_docx
from tools.processing.summarize_chunks import summarize_chunks

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
SOURCE_BUCKET = os.getenv("SOURCE_BUCKET", "centef-rag-bucket")


def clean_filename(filename: str) -> str:
    """Convert filename to source_id format."""
    # Remove extension
    name = Path(filename).stem
    # Convert to lowercase and replace spaces/special chars with hyphens
    source_id = re.sub(r'[^a-z0-9]+', '-', name.lower())
    # Remove leading/trailing hyphens
    source_id = source_id.strip('-')
    return source_id


def upload_to_gcs(local_path: str, source_id: str, filename: str) -> str:
    """Upload file to GCS and return URI."""
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(SOURCE_BUCKET.replace("gs://", ""))
    
    # Preserve original filename in GCS
    blob = bucket.blob(f"sources/{filename}")
    blob.upload_from_filename(local_path)
    
    gcs_uri = f"gs://{SOURCE_BUCKET}/sources/{filename}"
    logger.info(f"✓ Uploaded to {gcs_uri}")
    return gcs_uri


def process_single_file(file_path: str, force_reprocess: bool = False) -> bool:
    """
    Process a single PDF or DOCX file through the full pipeline.
    
    Args:
        file_path: Absolute path to the file
        force_reprocess: If True, reprocess even if already exists
    
    Returns:
        True if successful, False otherwise
    """
    try:
        filename = os.path.basename(file_path)
        source_id = clean_filename(filename)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing: {filename}")
        logger.info(f"Source ID: {source_id}")
        logger.info(f"{'='*80}\n")
        
        # Check if already exists in manifest
        existing_entry = get_manifest_entry(source_id)
        
        if existing_entry and not force_reprocess:
            if existing_entry.status == DocumentStatus.EMBEDDED.value:
                logger.info(f"⏭️  Skipping {filename} - already processed and embedded")
                return True
        
        # Determine file type
        file_ext = Path(file_path).suffix.lower()
        mimetype = "application/pdf" if file_ext == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        
        # Step 1: Upload to GCS (or check if exists)
        if not existing_entry:
            logger.info("Uploading to GCS...")
            gcs_uri = upload_to_gcs(file_path, source_id, filename)
            
            # Create manifest entry
            logger.info("✓ Creating manifest entry")
            entry = ManifestEntry(
                source_id=source_id,
                filename=filename,
                title=Path(filename).stem,
                mimetype=mimetype,
                source_uri=gcs_uri,
                status=DocumentStatus.PENDING_PROCESSING.value,
                ingested_by="batch_reprocess"
            )
            create_manifest_entry(entry)
        else:
            gcs_uri = existing_entry.source_uri
            logger.info(f"✓ Using existing GCS file: {gcs_uri}")
        
        # Step 2: Process file (extract chunks)
        logger.info("Processing file...")
        if file_ext == ".pdf":
            data_path = process_pdf(source_id, gcs_uri)
        elif file_ext == ".docx":
            data_path = process_docx(source_id, gcs_uri)
        else:
            logger.error(f"Unsupported file type: {file_ext}")
            return False
        
        logger.info("✓ Extracted chunks")
        
        # Step 3: Generate summary
        logger.info("Generating summary with Gemini...")
        summary_path = summarize_chunks(source_id)
        logger.info("✓ Generated summary")
        
        # Step 4: Auto-approve
        logger.info("Approving document...")
        update_manifest_entry(source_id, {
            "approved": True,
            "status": DocumentStatus.PENDING_EMBEDDING.value
        })
        logger.info("✓ Approved")
        
        # Note: Indexing is triggered automatically by manifest update
        logger.info("✓ Indexing will be triggered automatically")
        
        logger.info(f"\n✓✓✓ Successfully processed {filename} ✓✓✓\n")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to process {file_path}: {e}")
        logger.exception(e)
        return False


def reprocess_directory(directory: str, force_reprocess: bool = False):
    """Process all PDF and DOCX files in a directory."""
    directory_path = Path(directory)
    
    if not directory_path.exists():
        logger.error(f"Directory not found: {directory}")
        return
    
    # Find all PDF and DOCX files
    pdf_files = list(directory_path.glob("*.pdf"))
    docx_files = list(directory_path.glob("*.docx"))
    all_files = sorted(pdf_files + docx_files)
    
    if not all_files:
        logger.warning(f"No PDF or DOCX files found in {directory}")
        return
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Found {len(all_files)} files to process:")
    logger.info(f"  - {len(pdf_files)} PDFs")
    logger.info(f"  - {len(docx_files)} DOCX files")
    logger.info(f"Force reprocess: {force_reprocess}")
    logger.info(f"{'='*80}\n")
    
    successful = 0
    failed = 0
    skipped = 0
    
    for i, file_path in enumerate(all_files, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing file {i}/{len(all_files)}")
        logger.info(f"{'='*80}")
        
        result = process_single_file(str(file_path), force_reprocess)
        
        if result:
            # Check if it was actually processed or skipped
            if "⏭️" in str(result):
                skipped += 1
            else:
                successful += 1
        else:
            failed += 1
        
        # Small delay between files
        import time
        time.sleep(2)
    
    logger.info(f"\n{'='*80}")
    logger.info("Reprocessing Complete!")
    logger.info(f"Total: {len(all_files)} | Successful: {successful} | Failed: {failed} | Skipped: {skipped}")
    logger.info(f"{'='*80}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reprocess all files from CTF Essential Readings")
    parser.add_argument(
        "--directory",
        default=r"C:\Users\User\PycharmProjects\CENTEF\Data Samples v1\Data Samples v1\CTF - Essential Readings",
        help="Directory containing files to process"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reprocess even if files are already embedded"
    )
    
    args = parser.parse_args()
    
    reprocess_directory(args.directory, args.force)
