"""
Batch upload tool for processing multiple PDFs and DOCX files.
Walks through a directory, creates manifest entries, uploads files to GCS,
and processes them through the complete pipeline (chunking + summarization).
"""
import argparse
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import List, Tuple

from google.cloud import storage

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.manifest import ManifestEntry, create_manifest_entry, DocumentStatus
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


def find_documents(directory: str) -> List[Tuple[str, str]]:
    """
    Find all PDF and DOCX files in directory and subdirectories.

    Args:
        directory: Root directory to search

    Returns:
        List of tuples (file_path, mimetype)
    """
    logger.info(f"Searching for documents in {directory}")

    documents = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            file_lower = file.lower()
            file_path = os.path.join(root, file)

            if file_lower.endswith('.pdf'):
                documents.append((file_path, 'application/pdf'))
            elif file_lower.endswith('.docx'):
                documents.append((file_path, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'))

    logger.info(f"Found {len(documents)} documents")
    return documents


def upload_to_gcs(local_path: str, source_id: str) -> str:
    """
    Upload a file to GCS.

    Args:
        local_path: Local file path
        source_id: Source ID for GCS path

    Returns:
        GCS URI (gs://bucket/path)
    """
    logger.info(f"Uploading {local_path} to GCS")

    # Determine file extension
    _, ext = os.path.splitext(local_path)

    # Create GCS path
    gcs_path = f"sources/{source_id}{ext}"

    # Upload
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(SOURCE_BUCKET)
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(local_path)

    gcs_uri = f"gs://{SOURCE_BUCKET}/{gcs_path}"
    logger.info(f"Uploaded to {gcs_uri}")

    return gcs_uri


def process_document(file_path: str, mimetype: str, tags: List[str] = None,
                     ingested_by: str = "batch_upload", dry_run: bool = False,
                     skip_summarization: bool = False) -> str:
    """
    Process a single document: create manifest entry, upload to GCS, chunk, and summarize.

    Args:
        file_path: Local file path
        mimetype: MIME type of the file
        tags: Optional list of tags
        ingested_by: Source of ingestion
        dry_run: If True, only print what would be done without actually doing it
        skip_summarization: If True, skip the summarization step

    Returns:
        Source ID of the processed document
    """
    filename = os.path.basename(file_path)
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Processing {filename}")

    # Generate source_id
    source_id = str(uuid.uuid4())

    # Extract title (filename without extension)
    title = os.path.splitext(filename)[0]

    if dry_run:
        logger.info(f"[DRY RUN] Would create manifest entry for {filename} with source_id={source_id}")
        logger.info(f"[DRY RUN] Would upload {file_path} to GCS")
        logger.info(f"[DRY RUN] Would process as {mimetype}")
        if not skip_summarization:
            logger.info(f"[DRY RUN] Would summarize chunks")
        return source_id

    try:
        # Upload to GCS first
        gcs_uri = upload_to_gcs(file_path, source_id)

        # Create manifest entry
        entry = ManifestEntry(
            source_id=source_id,
            filename=filename,
            title=title,
            mimetype=mimetype,
            source_uri=gcs_uri,
            status=DocumentStatus.PENDING_PROCESSING,
            ingested_by=ingested_by,
            tags=tags or [],
            notes=f"Batch uploaded from {file_path}"
        )

        create_manifest_entry(entry)
        logger.info(f"Created manifest entry for {source_id}")

        # Process the document based on mimetype (creates chunks)
        if mimetype == 'application/pdf':
            chunks_path = process_pdf(source_id, gcs_uri)
            logger.info(f"Processed PDF, chunks: {chunks_path}")
        elif mimetype == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            chunks_path = process_docx(source_id, gcs_uri)
            logger.info(f"Processed DOCX, chunks: {chunks_path}")
        else:
            raise ValueError(f"Unsupported mimetype: {mimetype}")

        # Summarize chunks (extracts metadata and creates summary)
        if not skip_summarization:
            summary_path = summarize_chunks(source_id)
            logger.info(f"Generated summary: {summary_path}")
        else:
            logger.info(f"Skipping summarization for {source_id}")

        logger.info(f"✓ Successfully processed {filename} with source_id={source_id}")
        return source_id

    except Exception as e:
        logger.error(f"Error processing {filename}: {e}", exc_info=True)
        raise


def batch_process_directory(directory: str, tags: List[str] = None,
                           dry_run: bool = False, skip_errors: bool = True,
                           skip_summarization: bool = False) -> dict:
    """
    Process all PDF and DOCX files in a directory and subdirectories.

    Args:
        directory: Root directory to search
        tags: Optional list of tags to apply to all documents
        dry_run: If True, only print what would be done
        skip_errors: If True, continue processing even if individual files fail
        skip_summarization: If True, skip summarization step for all files

    Returns:
        Dictionary with processing statistics
    """
    if not os.path.exists(directory):
        raise ValueError(f"Directory does not exist: {directory}")

    if not os.path.isdir(directory):
        raise ValueError(f"Path is not a directory: {directory}")

    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Starting batch processing of {directory}")

    # Find all documents
    documents = find_documents(directory)

    if not documents:
        logger.warning(f"No PDF or DOCX files found in {directory}")
        return {"total": 0, "processed": 0, "failed": 0, "skipped": 0}

    stats = {
        "total": len(documents),
        "processed": 0,
        "failed": 0,
        "skipped": 0,
        "source_ids": []
    }

    # Process each document
    for i, (file_path, mimetype) in enumerate(documents, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing document {i}/{len(documents)}: {file_path}")
        logger.info(f"{'='*80}")

        try:
            source_id = process_document(
                file_path, mimetype, tags,
                dry_run=dry_run,
                skip_summarization=skip_summarization
            )
            stats["processed"] += 1
            stats["source_ids"].append(source_id)
            logger.info(f"✓ Successfully processed {i}/{len(documents)}: {os.path.basename(file_path)}")

        except Exception as e:
            stats["failed"] += 1
            logger.error(f"✗ Failed to process {i}/{len(documents)}: {os.path.basename(file_path)}")
            logger.error(f"  Error: {e}")

            if not skip_errors:
                logger.error("Stopping batch processing due to error (use --skip-errors to continue)")
                raise

    # Print summary
    logger.info(f"\n{'='*80}")
    logger.info("BATCH PROCESSING SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Total documents found: {stats['total']}")
    logger.info(f"Successfully processed: {stats['processed']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"{'='*80}\n")

    return stats


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Batch process PDFs and DOCX files from a directory"
    )
    parser.add_argument(
        "directory",
        help="Directory to search for PDF and DOCX files"
    )
    parser.add_argument(
        "--tags",
        nargs="+",
        help="Optional tags to apply to all documents (space-separated)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without actually doing it"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop processing on first error (default: skip errors and continue)"
    )
    parser.add_argument(
        "--skip-summarization",
        action="store_true",
        help="Skip the summarization step (only chunk documents)"
    )

    args = parser.parse_args()

    try:
        stats = batch_process_directory(
            args.directory,
            tags=args.tags,
            dry_run=args.dry_run,
            skip_errors=not args.fail_fast,
            skip_summarization=args.skip_summarization
        )

        if stats["failed"] > 0:
            return 1

        return 0

    except Exception as e:
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
