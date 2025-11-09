"""
Reprocess documents that had failed summaries.
This script re-runs summarization and indexing for documents with 'error' tags.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import get_manifest_entries, get_manifest_entry, update_manifest_entry, DocumentStatus
from tools.processing.summarize_chunks import summarize_chunks
from services.embedding.index_documents import index_document

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def reprocess_failed_summaries():
    """Find and reprocess documents with failed summaries."""
    logger.info("Loading manifest to find failed summaries...")
    
    entries = get_manifest_entries()
    
    # Find documents with 'error' or 'fallback' tags
    failed_docs = []
    for entry in entries:
        tags = entry.tags if hasattr(entry, 'tags') and entry.tags else []
        if "error" in tags or "fallback" in tags:
            source_id = entry.source_id
            failed_docs.append(source_id)
            logger.info(f"Found failed summary: {source_id}")
    
    if not failed_docs:
        logger.info("No failed summaries found!")
        return
    
    logger.info(f"\nFound {len(failed_docs)} documents with failed summaries")
    logger.info("=" * 80)
    
    for i, source_id in enumerate(failed_docs, 1):
        logger.info(f"\n[{i}/{len(failed_docs)}] Reprocessing: {source_id}")
        logger.info("=" * 80)
        
        try:
            # Step 1: Regenerate summary
            logger.info("Step 1: Regenerating summary with improved parser...")
            
            # Reset status to pending_summary to allow re-summarization
            update_manifest_entry(source_id, {
                "status": DocumentStatus.PENDING_SUMMARY.value,
                "tags": []  # Clear error tags
            })
            
            # Run summarization
            summary_path = summarize_chunks(source_id)
            logger.info(f"✓ Summary regenerated: {summary_path}")
            
            # Step 2: Re-approve (auto-approve for reprocessing)
            logger.info("Step 2: Auto-approving...")
            update_manifest_entry(source_id, {
                "approved": True,
                "status": DocumentStatus.PENDING_EMBEDDING.value
            })
            logger.info("✓ Approved")
            
            # Step 3: Re-index
            logger.info("Step 3: Re-indexing to Discovery Engine...")
            # Note: The manifest update will trigger indexing automatically
            # But we'll call it explicitly to ensure it happens now
            entry = get_manifest_entry(source_id)
            if entry and entry.status == DocumentStatus.PENDING_EMBEDDING.value:
                index_document(source_id)
                logger.info("✓ Re-indexed")
            
            logger.info(f"\n✓✓✓ Successfully reprocessed {source_id} ✓✓✓\n")
            
        except Exception as e:
            logger.error(f"❌ Failed to reprocess {source_id}: {e}")
            logger.exception(e)
            continue
    
    logger.info("\n" + "=" * 80)
    logger.info("Reprocessing complete!")
    logger.info("=" * 80)


if __name__ == "__main__":
    reprocess_failed_summaries()
