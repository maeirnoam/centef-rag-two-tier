"""
Check indexing status and manually trigger indexing for any pending documents.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import get_manifest_entries, DocumentStatus
from services.embedding.index_documents import index_document

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_and_index_pending():
    """Check for pending documents and trigger indexing."""
    logger.info("Loading manifest to check indexing status...")
    
    entries = get_manifest_entries()
    
    # Count by status
    status_counts = {}
    pending_embedding = []
    
    for entry in entries:
        status = entry.status
        status_counts[status] = status_counts.get(status, 0) + 1
        
        if status == DocumentStatus.PENDING_EMBEDDING.value:
            pending_embedding.append(entry)
    
    logger.info(f"\n{'='*80}")
    logger.info("Manifest Status Summary:")
    logger.info(f"{'='*80}")
    for status, count in sorted(status_counts.items()):
        logger.info(f"  {status}: {count} documents")
    logger.info(f"{'='*80}\n")
    
    if not pending_embedding:
        logger.info("✓ No documents pending indexing - all done!")
        return
    
    logger.info(f"Found {len(pending_embedding)} documents pending indexing")
    logger.info(f"{'='*80}\n")
    
    for i, entry in enumerate(pending_embedding, 1):
        logger.info(f"\n[{i}/{len(pending_embedding)}] Indexing: {entry.source_id}")
        logger.info(f"  Filename: {entry.filename}")
        logger.info("="*80)
        
        try:
            # Call index_document with the entry object
            index_document(entry)
            logger.info(f"✓ Successfully indexed {entry.source_id}\n")
            
        except Exception as e:
            logger.error(f"❌ Failed to index {entry.source_id}: {e}")
            logger.exception(e)
    
    logger.info(f"\n{'='*80}")
    logger.info("Indexing Complete!")
    logger.info(f"{'='*80}\n")
    
    # Check status again
    logger.info("Checking final status...")
    entries = get_manifest_entries()
    
    status_counts = {}
    for entry in entries:
        status = entry.status
        status_counts[status] = status_counts.get(status, 0) + 1
    
    logger.info(f"\n{'='*80}")
    logger.info("Final Status Summary:")
    logger.info(f"{'='*80}")
    for status, count in sorted(status_counts.items()):
        logger.info(f"  {status}: {count} documents")
    logger.info(f"{'='*80}\n")


if __name__ == "__main__":
    check_and_index_pending()
