"""
Clean up orphaned documents from GCS and Vertex AI Search.
Finds documents that exist in GCS/Vertex AI but not in manifest and deletes them.
"""
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Set

from google.cloud import storage
from google.cloud import discoveryengine_v1beta as discoveryengine

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.manifest import get_manifest_entries

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
VERTEX_SEARCH_LOCATION = os.getenv("VERTEX_SEARCH_LOCATION", "global")
CHUNKS_DATASTORE_ID = os.getenv("CHUNKS_DATASTORE_ID")
SUMMARIES_DATASTORE_ID = os.getenv("SUMMARIES_DATASTORE_ID")
TARGET_BUCKET = os.getenv("TARGET_BUCKET", "centef-rag-chunks")
SOURCE_BUCKET = os.getenv("SOURCE_BUCKET", "centef-rag-bucket")


def get_valid_source_ids() -> Set[str]:
    """
    Get set of valid source_ids from manifest.

    Returns:
        Set of source_ids that should exist
    """
    logger.info("Loading manifest entries...")
    entries = get_manifest_entries()
    valid_ids = {entry.source_id for entry in entries}
    logger.info(f"Found {len(valid_ids)} valid source_ids in manifest")
    return valid_ids


def cleanup_orphaned_chunks(valid_source_ids: Set[str], dry_run: bool = False) -> dict:
    """
    Clean up orphaned chunk documents from Vertex AI Search.

    Args:
        valid_source_ids: Set of source_ids that should exist
        dry_run: If True, only report what would be deleted

    Returns:
        Dict with statistics
    """
    logger.info("\n" + "="*80)
    logger.info("CLEANING UP ORPHANED CHUNKS FROM VERTEX AI")
    logger.info("="*80 + "\n")

    client = discoveryengine.DocumentServiceClient()

    parent = (
        f"projects/{PROJECT_ID}/"
        f"locations/{VERTEX_SEARCH_LOCATION}/"
        f"collections/default_collection/"
        f"dataStores/{CHUNKS_DATASTORE_ID}/"
        f"branches/default_branch"
    )

    stats = {
        "total_chunks": 0,
        "orphaned_chunks": 0,
        "deleted_chunks": 0,
        "failed_chunks": 0
    }

    orphaned_docs = []

    try:
        request = discoveryengine.ListDocumentsRequest(
            parent=parent,
            page_size=1000
        )

        logger.info("Listing all chunk documents in Vertex AI...")
        page_result = client.list_documents(request=request)

        for document in page_result:
            stats["total_chunks"] += 1

            # Extract source_id from document name
            # Document IDs follow pattern: {source_id}_page_{n} or {source_id}_chunk_{n}
            doc_id = document.name.split('/')[-1]

            # Try to extract source_id (everything before _page_ or _chunk_)
            if '_page_' in doc_id:
                source_id = doc_id.split('_page_')[0]
            elif '_chunk_' in doc_id:
                source_id = doc_id.split('_chunk_')[0]
            else:
                # Unknown format, check if entire doc_id is a source_id
                source_id = doc_id

            # Check if source_id is valid
            if source_id not in valid_source_ids:
                stats["orphaned_chunks"] += 1
                orphaned_docs.append({
                    "name": document.name,
                    "id": doc_id,
                    "source_id": source_id
                })

        logger.info(f"Found {stats['total_chunks']} total chunk documents")
        logger.info(f"Found {stats['orphaned_chunks']} orphaned chunk documents")

        if orphaned_docs:
            logger.info(f"\nSample orphaned chunks (first 10):")
            for i, doc in enumerate(orphaned_docs[:10], 1):
                logger.info(f"  {i}. {doc['id']} (source: {doc['source_id']})")

        if dry_run:
            logger.info(f"\n[DRY RUN] Would delete {stats['orphaned_chunks']} orphaned chunks")
            return stats

        # Actually delete orphaned chunks
        if stats["orphaned_chunks"] > 0:
            logger.info(f"\nDeleting {stats['orphaned_chunks']} orphaned chunks...")

            for i, doc in enumerate(orphaned_docs, 1):
                try:
                    delete_request = discoveryengine.DeleteDocumentRequest(
                        name=doc["name"]
                    )
                    client.delete_document(request=delete_request)
                    stats["deleted_chunks"] += 1

                    if (i % 10 == 0) or (i == len(orphaned_docs)):
                        logger.info(f"  Deleted {i}/{len(orphaned_docs)} chunks...")

                except Exception as e:
                    stats["failed_chunks"] += 1
                    logger.warning(f"  Failed to delete {doc['id']}: {e}")

            logger.info(f"✓ Deleted {stats['deleted_chunks']} orphaned chunks")
            if stats["failed_chunks"] > 0:
                logger.warning(f"⚠ Failed to delete {stats['failed_chunks']} chunks")

    except Exception as e:
        logger.error(f"Error during chunk cleanup: {e}", exc_info=True)
        raise

    return stats


def cleanup_orphaned_summaries(valid_source_ids: Set[str], dry_run: bool = False) -> dict:
    """
    Clean up orphaned summary documents from Vertex AI Search.

    Args:
        valid_source_ids: Set of source_ids that should exist
        dry_run: If True, only report what would be deleted

    Returns:
        Dict with statistics
    """
    logger.info("\n" + "="*80)
    logger.info("CLEANING UP ORPHANED SUMMARIES FROM VERTEX AI")
    logger.info("="*80 + "\n")

    client = discoveryengine.DocumentServiceClient()

    parent = (
        f"projects/{PROJECT_ID}/"
        f"locations/{VERTEX_SEARCH_LOCATION}/"
        f"collections/default_collection/"
        f"dataStores/{SUMMARIES_DATASTORE_ID}/"
        f"branches/default_branch"
    )

    stats = {
        "total_summaries": 0,
        "orphaned_summaries": 0,
        "deleted_summaries": 0,
        "failed_summaries": 0
    }

    orphaned_docs = []

    try:
        request = discoveryengine.ListDocumentsRequest(
            parent=parent,
            page_size=1000
        )

        logger.info("Listing all summary documents in Vertex AI...")
        page_result = client.list_documents(request=request)

        for document in page_result:
            stats["total_summaries"] += 1

            # Summary document ID is the source_id itself
            doc_id = document.name.split('/')[-1]
            source_id = doc_id

            # Check if source_id is valid
            if source_id not in valid_source_ids:
                stats["orphaned_summaries"] += 1
                orphaned_docs.append({
                    "name": document.name,
                    "id": doc_id,
                    "source_id": source_id
                })

        logger.info(f"Found {stats['total_summaries']} total summary documents")
        logger.info(f"Found {stats['orphaned_summaries']} orphaned summary documents")

        if orphaned_docs:
            logger.info(f"\nSample orphaned summaries (first 10):")
            for i, doc in enumerate(orphaned_docs[:10], 1):
                logger.info(f"  {i}. {doc['id']}")

        if dry_run:
            logger.info(f"\n[DRY RUN] Would delete {stats['orphaned_summaries']} orphaned summaries")
            return stats

        # Actually delete orphaned summaries
        if stats["orphaned_summaries"] > 0:
            logger.info(f"\nDeleting {stats['orphaned_summaries']} orphaned summaries...")

            for i, doc in enumerate(orphaned_docs, 1):
                try:
                    delete_request = discoveryengine.DeleteDocumentRequest(
                        name=doc["name"]
                    )
                    client.delete_document(request=delete_request)
                    stats["deleted_summaries"] += 1

                    if (i % 10 == 0) or (i == len(orphaned_docs)):
                        logger.info(f"  Deleted {i}/{len(orphaned_docs)} summaries...")

                except Exception as e:
                    stats["failed_summaries"] += 1
                    logger.warning(f"  Failed to delete {doc['id']}: {e}")

            logger.info(f"✓ Deleted {stats['deleted_summaries']} orphaned summaries")
            if stats["failed_summaries"] > 0:
                logger.warning(f"⚠ Failed to delete {stats['failed_summaries']} summaries")

    except Exception as e:
        logger.error(f"Error during summary cleanup: {e}", exc_info=True)
        raise

    return stats


def cleanup_orphaned_gcs_files(valid_source_ids: Set[str], dry_run: bool = False) -> dict:
    """
    Clean up orphaned files from GCS buckets.

    Args:
        valid_source_ids: Set of source_ids that should exist
        dry_run: If True, only report what would be deleted

    Returns:
        Dict with statistics
    """
    logger.info("\n" + "="*80)
    logger.info("CLEANING UP ORPHANED FILES FROM GCS")
    logger.info("="*80 + "\n")

    storage_client = storage.Client(project=PROJECT_ID)

    stats = {
        "chunks_files_checked": 0,
        "summaries_files_checked": 0,
        "orphaned_chunks_files": 0,
        "orphaned_summaries_files": 0,
        "deleted_chunks_files": 0,
        "deleted_summaries_files": 0,
        "failed_deletions": 0
    }

    # Clean up chunks files (data/*.jsonl)
    logger.info(f"Checking chunks files in gs://{TARGET_BUCKET}/data/...")
    bucket = storage_client.bucket(TARGET_BUCKET.replace("gs://", ""))

    orphaned_chunks = []
    for blob in bucket.list_blobs(prefix="data/"):
        if blob.name.endswith(".jsonl"):
            stats["chunks_files_checked"] += 1
            # Extract source_id from path: data/{source_id}.jsonl
            source_id = blob.name.split("/")[-1].replace(".jsonl", "")

            if source_id not in valid_source_ids:
                stats["orphaned_chunks_files"] += 1
                orphaned_chunks.append(blob)

    logger.info(f"Found {stats['chunks_files_checked']} chunks files")
    logger.info(f"Found {stats['orphaned_chunks_files']} orphaned chunks files")

    # Clean up summary files (summaries/*.jsonl)
    logger.info(f"\nChecking summary files in gs://{TARGET_BUCKET}/summaries/...")

    orphaned_summaries = []
    for blob in bucket.list_blobs(prefix="summaries/"):
        if blob.name.endswith(".jsonl"):
            stats["summaries_files_checked"] += 1
            # Extract source_id from path: summaries/{source_id}.jsonl
            source_id = blob.name.split("/")[-1].replace(".jsonl", "")

            if source_id not in valid_source_ids:
                stats["orphaned_summaries_files"] += 1
                orphaned_summaries.append(blob)

    logger.info(f"Found {stats['summaries_files_checked']} summary files")
    logger.info(f"Found {stats['orphaned_summaries_files']} orphaned summary files")

    if dry_run:
        logger.info(f"\n[DRY RUN] Would delete:")
        logger.info(f"  {stats['orphaned_chunks_files']} orphaned chunks files")
        logger.info(f"  {stats['orphaned_summaries_files']} orphaned summary files")
        return stats

    # Actually delete orphaned files
    total_to_delete = len(orphaned_chunks) + len(orphaned_summaries)
    if total_to_delete > 0:
        logger.info(f"\nDeleting {total_to_delete} orphaned GCS files...")

        for blob in orphaned_chunks:
            try:
                blob.delete()
                stats["deleted_chunks_files"] += 1
            except Exception as e:
                stats["failed_deletions"] += 1
                logger.warning(f"Failed to delete {blob.name}: {e}")

        for blob in orphaned_summaries:
            try:
                blob.delete()
                stats["deleted_summaries_files"] += 1
            except Exception as e:
                stats["failed_deletions"] += 1
                logger.warning(f"Failed to delete {blob.name}: {e}")

        logger.info(f"✓ Deleted {stats['deleted_chunks_files']} chunks files")
        logger.info(f"✓ Deleted {stats['deleted_summaries_files']} summary files")
        if stats["failed_deletions"] > 0:
            logger.warning(f"⚠ Failed to delete {stats['failed_deletions']} files")

    return stats


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Clean up orphaned documents from GCS and Vertex AI Search"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without actually doing it"
    )
    parser.add_argument(
        "--vertex-only",
        action="store_true",
        help="Only clean up Vertex AI Search, skip GCS files"
    )
    parser.add_argument(
        "--gcs-only",
        action="store_true",
        help="Only clean up GCS files, skip Vertex AI Search"
    )

    args = parser.parse_args()

    try:
        # Get valid source_ids from manifest
        valid_source_ids = get_valid_source_ids()

        all_stats = {}

        # Clean up Vertex AI Search
        if not args.gcs_only:
            chunks_stats = cleanup_orphaned_chunks(valid_source_ids, dry_run=args.dry_run)
            summaries_stats = cleanup_orphaned_summaries(valid_source_ids, dry_run=args.dry_run)
            all_stats["chunks"] = chunks_stats
            all_stats["summaries"] = summaries_stats

        # Clean up GCS files
        if not args.vertex_only:
            gcs_stats = cleanup_orphaned_gcs_files(valid_source_ids, dry_run=args.dry_run)
            all_stats["gcs"] = gcs_stats

        # Print final summary
        logger.info("\n" + "="*80)
        logger.info("CLEANUP SUMMARY")
        logger.info("="*80)

        if "chunks" in all_stats:
            logger.info(f"\nVertex AI Chunks Datastore:")
            logger.info(f"  Total documents: {all_stats['chunks']['total_chunks']}")
            logger.info(f"  Orphaned: {all_stats['chunks']['orphaned_chunks']}")
            if not args.dry_run:
                logger.info(f"  Deleted: {all_stats['chunks']['deleted_chunks']}")
                if all_stats['chunks']['failed_chunks'] > 0:
                    logger.info(f"  Failed: {all_stats['chunks']['failed_chunks']}")

        if "summaries" in all_stats:
            logger.info(f"\nVertex AI Summaries Datastore:")
            logger.info(f"  Total documents: {all_stats['summaries']['total_summaries']}")
            logger.info(f"  Orphaned: {all_stats['summaries']['orphaned_summaries']}")
            if not args.dry_run:
                logger.info(f"  Deleted: {all_stats['summaries']['deleted_summaries']}")
                if all_stats['summaries']['failed_summaries'] > 0:
                    logger.info(f"  Failed: {all_stats['summaries']['failed_summaries']}")

        if "gcs" in all_stats:
            logger.info(f"\nGCS Files:")
            logger.info(f"  Chunks files checked: {all_stats['gcs']['chunks_files_checked']}")
            logger.info(f"  Summaries files checked: {all_stats['gcs']['summaries_files_checked']}")
            logger.info(f"  Orphaned chunks files: {all_stats['gcs']['orphaned_chunks_files']}")
            logger.info(f"  Orphaned summaries files: {all_stats['gcs']['orphaned_summaries_files']}")
            if not args.dry_run:
                logger.info(f"  Deleted chunks files: {all_stats['gcs']['deleted_chunks_files']}")
                logger.info(f"  Deleted summaries files: {all_stats['gcs']['deleted_summaries_files']}")
                if all_stats['gcs']['failed_deletions'] > 0:
                    logger.info(f"  Failed deletions: {all_stats['gcs']['failed_deletions']}")

        logger.info("="*80)

        return 0

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
