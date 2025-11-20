"""
Approve pending documents and trigger indexing.
Updates documents from PENDING_APPROVAL to PENDING_EMBEDDING status,
which automatically triggers indexing via the manifest update hook.
"""
import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.manifest import get_manifest_entries, update_manifest_entry, DocumentStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def approve_and_trigger_embedding(source_ids=None, tags=None):
    """
    Approve documents and trigger embedding.

    Args:
        source_ids: Optional list of specific source_ids to approve
        tags: Optional list of tags to filter by

    Returns:
        Dict with statistics
    """
    logger.info("Loading manifest entries...")

    # Get all entries with PENDING_APPROVAL status
    entries = get_manifest_entries(status=DocumentStatus.PENDING_APPROVAL)

    logger.info(f"Found {len(entries)} documents with PENDING_APPROVAL status")

    # Filter by source_ids if provided
    if source_ids:
        entries = [e for e in entries if e.source_id in source_ids]
        logger.info(f"Filtered to {len(entries)} documents by source_id")

    # Filter by tags if provided
    if tags:
        entries = [e for e in entries if any(tag in e.tags for tag in tags)]
        logger.info(f"Filtered to {len(entries)} documents by tags")

    if not entries:
        logger.warning("No matching documents found")
        return {"total": 0, "approved": 0, "failed": 0}

    stats = {
        "total": len(entries),
        "approved": 0,
        "failed": 0,
        "source_ids": []
    }

    logger.info(f"\nApproving and triggering embedding for {len(entries)} documents...")

    for i, entry in enumerate(entries, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing {i}/{len(entries)}: {entry.filename}")
        logger.info(f"Source ID: {entry.source_id}")
        logger.info(f"{'='*80}")

        try:
            # Update status to PENDING_EMBEDDING
            # This will automatically trigger the embedding process
            # via the trigger_embedding_for_source() function in manifest.py
            update_manifest_entry(entry.source_id, {
                "status": DocumentStatus.PENDING_EMBEDDING,
                "approved": True
            })

            stats["approved"] += 1
            stats["source_ids"].append(entry.source_id)
            logger.info(f"✓ Approved and triggered embedding for {i}/{len(entries)}: {entry.filename}")

        except Exception as e:
            stats["failed"] += 1
            logger.error(f"✗ Failed to approve {i}/{len(entries)}: {entry.filename}")
            logger.error(f"  Error: {e}")

    # Print summary
    logger.info(f"\n{'='*80}")
    logger.info("APPROVAL AND EMBEDDING SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Total documents: {stats['total']}")
    logger.info(f"Successfully approved and triggered: {stats['approved']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"{'='*80}\n")

    return stats


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Approve pending documents and trigger indexing"
    )
    parser.add_argument(
        "--source-ids",
        nargs="+",
        help="Optional specific source IDs to approve (space-separated)"
    )
    parser.add_argument(
        "--tags",
        nargs="+",
        help="Optional tags to filter by (space-separated)"
    )

    args = parser.parse_args()

    try:
        stats = approve_and_trigger_embedding(
            source_ids=args.source_ids,
            tags=args.tags
        )

        if stats["failed"] > 0:
            return 1

        return 0

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
