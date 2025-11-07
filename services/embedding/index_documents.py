"""
Document indexing service for CENTEF RAG system.
Indexes chunks and summaries into Vertex AI Search datastores.
"""
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

from google.cloud import storage
from google.cloud import discoveryengine_v1beta as discoveryengine
# TODO: Import proper Discovery Engine client libraries
# from google.cloud.discoveryengine_v1beta import DocumentServiceClient
# from google.cloud.discoveryengine_v1beta.types import Document

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.schemas import (
    Chunk, Summary, 
    read_chunks_from_jsonl, read_summary_from_jsonl,
    convert_to_discovery_engine_format,
    convert_summary_to_discovery_engine_format
)
from shared.manifest import ManifestEntry, update_manifest_entry, DocumentStatus

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


def download_from_gcs(gcs_path: str) -> str:
    """
    Download file from GCS to local temp.
    
    Args:
        gcs_path: GCS path (gs://bucket/path)
    
    Returns:
        Local file path
    """
    if not gcs_path.startswith("gs://"):
        return gcs_path
    
    # Parse GCS path
    parts = gcs_path.replace("gs://", "").split("/", 1)
    bucket_name = parts[0]
    blob_path = parts[1]
    
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    
    local_path = f"/tmp/{blob_path.replace('/', '_')}"
    blob.download_to_filename(local_path)
    
    logger.info(f"Downloaded {gcs_path} to {local_path}")
    return local_path


def index_chunks_to_discovery_engine(entry: ManifestEntry) -> None:
    """
    Index chunks into Vertex AI Search chunk datastore.
    
    Args:
        entry: ManifestEntry with data_path to chunks
    """
    logger.info(f"Indexing chunks for source_id={entry.source_id}")
    
    # Download chunks
    local_path = download_from_gcs(entry.data_path)
    chunks = read_chunks_from_jsonl(local_path)
    
    logger.info(f"Read {len(chunks)} chunks from {entry.data_path}")
    
    # TODO: Initialize Discovery Engine client
    # client = DocumentServiceClient()
    
    # Build parent path for datastore
    parent = (
        f"projects/{PROJECT_ID}/"
        f"locations/{VERTEX_SEARCH_LOCATION}/"
        f"collections/default_collection/"
        f"dataStores/{CHUNKS_DATASTORE_ID}"
    )
    
    logger.info(f"Indexing to datastore: {parent}")
    
    # Convert chunks to Discovery Engine format
    documents = []
    for chunk in chunks:
        doc = convert_to_discovery_engine_format(chunk)
        documents.append(doc)
    
    # TODO: Import documents using Discovery Engine API
    # Option 1: Import from GCS JSONL directly
    # request = discoveryengine.ImportDocumentsRequest(
    #     parent=parent,
    #     gcs_source=discoveryengine.GcsSource(
    #         input_uris=[entry.data_path],
    #         data_schema="content"
    #     ),
    #     reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL
    # )
    # operation = client.import_documents(request=request)
    # response = operation.result()
    
    # Option 2: Create documents individually
    # for doc_dict in documents:
    #     doc = discoveryengine.Document(**doc_dict)
    #     request = discoveryengine.CreateDocumentRequest(
    #         parent=parent,
    #         document=doc,
    #         document_id=doc.id
    #     )
    #     response = client.create_document(request=request)
    
    logger.info(f"Successfully indexed {len(chunks)} chunks (placeholder - implement Discovery Engine API)")


def index_summaries_to_discovery_engine(entry: ManifestEntry) -> None:
    """
    Index summary into Vertex AI Search summary datastore.
    
    Args:
        entry: ManifestEntry with summary_path
    """
    logger.info(f"Indexing summary for source_id={entry.source_id}")
    
    # Download summary
    local_path = download_from_gcs(entry.summary_path)
    summary = read_summary_from_jsonl(local_path)
    
    logger.info(f"Read summary from {entry.summary_path}")
    
    # TODO: Initialize Discovery Engine client
    # client = DocumentServiceClient()
    
    # Build parent path for datastore
    parent = (
        f"projects/{PROJECT_ID}/"
        f"locations/{VERTEX_SEARCH_LOCATION}/"
        f"collections/default_collection/"
        f"dataStores/{SUMMARIES_DATASTORE_ID}"
    )
    
    logger.info(f"Indexing to datastore: {parent}")
    
    # Convert summary to Discovery Engine format
    doc = convert_summary_to_discovery_engine_format(summary)
    
    # TODO: Import document using Discovery Engine API
    # Similar to chunks above
    
    logger.info(f"Successfully indexed summary (placeholder - implement Discovery Engine API)")


def index_document(entry: ManifestEntry) -> None:
    """
    Index both chunks and summary for a document.
    
    Args:
        entry: ManifestEntry to index
    """
    logger.info(f"Starting document indexing for source_id={entry.source_id}")
    
    try:
        # Validate status
        if entry.status != DocumentStatus.PENDING_EMBEDDING:
            logger.warning(
                f"Entry status is {entry.status}, expected {DocumentStatus.PENDING_EMBEDDING}. "
                f"Continuing anyway."
            )
        
        # Index chunks
        if entry.data_path:
            index_chunks_to_discovery_engine(entry)
        else:
            logger.warning(f"No data_path found for {entry.source_id}, skipping chunk indexing")
        
        # Index summary
        if entry.summary_path:
            index_summaries_to_discovery_engine(entry)
        else:
            logger.warning(f"No summary_path found for {entry.source_id}, skipping summary indexing")
        
        # Update manifest status to embedded
        update_manifest_entry(entry.source_id, {
            "status": DocumentStatus.EMBEDDED
        })
        
        logger.info(f"Successfully indexed document {entry.source_id} and updated status to {DocumentStatus.EMBEDDED}")
        
    except Exception as e:
        logger.error(f"Error indexing document {entry.source_id}: {e}", exc_info=True)
        
        # Update manifest to error status
        update_manifest_entry(entry.source_id, {
            "status": DocumentStatus.ERROR,
            "notes": f"Indexing error: {str(e)}"
        })
        
        raise


def main():
    """CLI entry point for testing."""
    import argparse
    from shared.manifest import get_manifest_entry
    
    parser = argparse.ArgumentParser(description="Index document into Discovery Engine")
    parser.add_argument("--source-id", required=True, help="Source ID from manifest")
    
    args = parser.parse_args()
    
    try:
        entry = get_manifest_entry(args.source_id)
        if not entry:
            logger.error(f"Manifest entry not found for source_id={args.source_id}")
            return 1
        
        index_document(entry)
        print(f"Successfully indexed document {args.source_id}")
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
