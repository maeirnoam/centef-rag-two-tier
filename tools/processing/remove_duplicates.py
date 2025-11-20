"""
Remove duplicate entries from the manifest.
Keeps the oldest entry for each filename and removes duplicates.
"""
import argparse
import logging
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.manifest import get_manifest_entries, _write_manifest_entries, DocumentStatus
from shared.source_management import delete_source_completely

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def remove_duplicates(dry_run=False, delete_completely=False):
    """
    Remove duplicate manifest entries, keeping the oldest entry for each filename.

    Args:
        dry_run: If True, only print what would be done without actually doing it
        delete_completely: If True, also delete GCS files and Vertex AI indexed documents

    Returns:
        Dict with statistics
    """
    logger.info("Loading manifest entries...")
    entries = get_manifest_entries()

    logger.info(f"Total entries: {len(entries)}")

    # Group by filename
    filename_to_entries = defaultdict(list)
    for entry in entries:
        filename_to_entries[entry.filename].append(entry)

    # Find duplicates
    duplicates_info = []
    entries_to_keep = []
    entries_to_remove = []

    for filename, file_entries in filename_to_entries.items():
        if len(file_entries) == 1:
            # No duplicates, keep it
            entries_to_keep.append(file_entries[0])
        else:
            # Duplicates found - keep the one with the best status
            # Priority: embedded > pending_embedding > pending_approval > pending_summary > pending_processing > error
            status_priority = {
                DocumentStatus.EMBEDDED: 0,
                DocumentStatus.PENDING_EMBEDDING: 1,
                DocumentStatus.PENDING_APPROVAL: 2,
                DocumentStatus.PENDING_SUMMARY: 3,
                DocumentStatus.PENDING_PROCESSING: 4,
                DocumentStatus.ERROR: 5
            }

            # Sort by status priority (best first), then by created_at (oldest first)
            sorted_entries = sorted(
                file_entries,
                key=lambda e: (
                    status_priority.get(e.status, 99),
                    datetime.fromisoformat(e.created_at)
                )
            )

            # Keep the best one
            keep = sorted_entries[0]
            remove = sorted_entries[1:]

            entries_to_keep.append(keep)
            entries_to_remove.extend(remove)

            duplicates_info.append({
                'filename': filename,
                'count': len(file_entries),
                'keeping': keep.source_id,
                'keeping_status': keep.status,
                'removing': [e.source_id for e in remove],
                'removing_statuses': [e.status for e in remove]
            })

    stats = {
        'total_before': len(entries),
        'total_after': len(entries_to_keep),
        'removed': len(entries_to_remove),
        'duplicate_files': len(duplicates_info)
    }

    logger.info(f"\n{'='*80}")
    logger.info("DUPLICATE ANALYSIS")
    logger.info(f"{'='*80}")
    logger.info(f"Total entries before: {stats['total_before']}")
    logger.info(f"Unique files: {len(filename_to_entries)}")
    logger.info(f"Files with duplicates: {stats['duplicate_files']}")
    logger.info(f"Entries to remove: {stats['removed']}")
    logger.info(f"Entries after cleanup: {stats['total_after']}")
    logger.info(f"{'='*80}\n")

    if duplicates_info:
        logger.info("Sample duplicates (first 10):")
        for i, dup in enumerate(duplicates_info[:10], 1):
            try:
                logger.info(f"\n{i}. {dup['filename']}")
            except:
                logger.info(f"\n{i}. [filename with special characters]")
            logger.info(f"   Total copies: {dup['count']}")
            logger.info(f"   Keeping: {dup['keeping']} (status: {dup['keeping_status']})")
            logger.info(f"   Removing: {len(dup['removing'])} copies")
            for remove_id, status in zip(dup['removing'], dup['removing_statuses']):
                logger.info(f"     - {remove_id} (status: {status})")

    if dry_run:
        logger.info(f"\n[DRY RUN] Would remove {stats['removed']} duplicate entries")
        return stats

    # Actually remove duplicates
    logger.info(f"\nRemoving {stats['removed']} duplicate entries...")
    _write_manifest_entries(entries_to_keep)
    logger.info("✓ Duplicates removed successfully!")

    return stats


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Remove duplicate entries from manifest"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without actually doing it"
    )

    args = parser.parse_args()

    try:
        stats = remove_duplicates(dry_run=args.dry_run)

        if not args.dry_run:
            logger.info(f"\n{'='*80}")
            logger.info("CLEANUP COMPLETE")
            logger.info(f"{'='*80}")
            logger.info(f"Removed {stats['removed']} duplicate entries")
            logger.info(f"Manifest now has {stats['total_after']} unique entries")
            logger.info(f"{'='*80}")

        return 0

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
