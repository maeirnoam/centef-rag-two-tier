"""
Source management utilities for CENTEF RAG system.
Handles cascading deletion and source lifecycle operations.
"""
import logging
import os
from typing import Dict, Any, Optional, Tuple

from google.cloud import storage
from google.cloud import discoveryengine_v1beta as discoveryengine

from .manifest import get_manifest_entry, ManifestEntry

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
SOURCE_BUCKET = os.getenv("SOURCE_BUCKET", "centef-rag-bucket")


def _parse_gcs_uri(gcs_uri: str) -> Tuple[str, str]:
    """
    Parse a gs:// URI into bucket and blob path.
    """
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Unsupported GCS URI: {gcs_uri}")
    
    remainder = gcs_uri[len("gs://") :]
    if "/" not in remainder:
        raise ValueError(f"GCS URI missing object path: {gcs_uri}")
    
    bucket, blob_path = remainder.split("/", 1)
    if not bucket or not blob_path:
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")
    
    return bucket, blob_path


def _delete_gcs_blob(gcs_uri: str, storage_client: storage.Client) -> Tuple[bool, Optional[str]]:
    """
    Delete a blob referenced by a gs:// URI.
    
    Returns:
        (success_or_missing, error_message)
    """
    try:
        bucket_name, blob_path = _parse_gcs_uri(gcs_uri)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        if blob.exists():
            blob.delete()
            logger.info(f"Deleted GCS object: {gcs_uri}")
        else:
            logger.warning(f"GCS object not found (already deleted): {gcs_uri}")
        return True, None
    except Exception as exc:
        logger.error(f"Failed to delete GCS object {gcs_uri}: {exc}")
        return False, str(exc)


def delete_source_completely(source_id: str) -> Dict[str, Any]:
    """
    Completely delete a source and all its associated data.
    
    This performs cascading deletion of:
    1. Source file from GCS (gs://{bucket}/sources/)
    2. Chunks JSONL from GCS (gs://{bucket}/data/{source_id}.jsonl)
    3. Summary JSONL from GCS (gs://{bucket}/summaries/{source_id}.jsonl)
    4. All indexed chunk documents from Discovery Engine chunks datastore
    5. Indexed summary document from Discovery Engine summaries datastore
    6. Manifest entry from manifest.jsonl
    
    Args:
        source_id: The source_id to delete
        
    Returns:
        Dict with deletion results: {
            "source_id": str,
            "success": bool,
            "deleted": {
                "source_file": bool,
                "chunks_file": bool,
                "summary_file": bool,
                "indexed_chunks": int (count),
                "indexed_summary": bool,
                "manifest_entry": bool
            },
            "errors": List[str]
        }
    """
    logger.info(f"Starting complete deletion for source_id={source_id}")
    
    result = {
        "source_id": source_id,
        "success": False,
        "deleted": {
            "source_file": False,
            "chunks_file": False,
            "summary_file": False,
            "indexed_chunks": 0,
            "indexed_summary": False,
            "manifest_entry": False
        },
        "errors": []
    }
    
    # Get manifest entry to find file paths
    entry = get_manifest_entry(source_id)
    if not entry:
        result["errors"].append(f"Source {source_id} not found in manifest")
        logger.warning(f"Source {source_id} not found in manifest")
        return result
    
    # Initialize GCS client
    storage_client = storage.Client(project=PROJECT_ID)

    def _delete_and_track(uri: Optional[str], key: str, label: str, fallback: Optional[str] = None):
        target_uri = uri or fallback
        if not target_uri:
            return

        if not target_uri.startswith("gs://"):
            logger.warning(f"Skipping {label} deletion for non-GCS URI: {target_uri}")
            return

        success, error = _delete_gcs_blob(target_uri, storage_client)
        result["deleted"][key] = success
        if error:
            result["errors"].append(f"{label}: {error}")

    # 1. Delete source file from GCS
    source_fallback = None
    if not entry.source_uri and entry.filename:
        source_fallback = f"gs://{SOURCE_BUCKET}/sources/{entry.filename}"
    _delete_and_track(entry.source_uri, "source_file", "source file", fallback=source_fallback)
    
    # 2. Delete chunks JSONL from GCS
    _delete_and_track(entry.data_path, "chunks_file", "chunks file")
    
    # 3. Delete summary JSONL from GCS
    _delete_and_track(entry.summary_path, "summary_file", "summary file")
    
    # 4. Delete indexed chunks from Discovery Engine
    try:
        chunks_deleted = delete_indexed_chunks(source_id)
        result["deleted"]["indexed_chunks"] = chunks_deleted
        logger.info(f"Deleted {chunks_deleted} indexed chunks")
    except Exception as e:
        error_msg = f"Failed to delete indexed chunks: {str(e)}"
        logger.error(error_msg)
        result["errors"].append(error_msg)
    
    # 5. Delete indexed summary from Discovery Engine
    try:
        summary_deleted = delete_indexed_summary(source_id)
        result["deleted"]["indexed_summary"] = summary_deleted
        logger.info(f"Deleted indexed summary: {summary_deleted}")
    except Exception as e:
        error_msg = f"Failed to delete indexed summary: {str(e)}"
        logger.error(error_msg)
        result["errors"].append(error_msg)
    
    # 6. Delete manifest entry
    try:
        from .manifest import delete_manifest_entry
        deleted = delete_manifest_entry(source_id)
        result["deleted"]["manifest_entry"] = deleted
        logger.info(f"Deleted manifest entry: {deleted}")
    except Exception as e:
        error_msg = f"Failed to delete manifest entry: {str(e)}"
        logger.error(error_msg)
        result["errors"].append(error_msg)
    
    # Determine overall success
    result["success"] = len(result["errors"]) == 0
    
    logger.info(f"Deletion complete for {source_id}: success={result['success']}")
    return result


def delete_indexed_chunks(source_id: str) -> int:
    """
    Delete all indexed chunks for a source from Discovery Engine.
    
    Args:
        source_id: The source_id whose chunks to delete
        
    Returns:
        Number of chunks deleted
    """
    client = discoveryengine.DocumentServiceClient()
    
    parent = (
        f"projects/{PROJECT_ID}/"
        f"locations/{VERTEX_SEARCH_LOCATION}/"
        f"collections/default_collection/"
        f"dataStores/{CHUNKS_DATASTORE_ID}/"
        f"branches/default_branch"
    )
    
    # List all documents and delete those matching source_id
    deleted_count = 0
    
    try:
        request = discoveryengine.ListDocumentsRequest(
            parent=parent,
            page_size=1000
        )
        
        page_result = client.list_documents(request=request)
        
        for document in page_result:
            # Check if document belongs to this source_id
            # Document IDs follow pattern: {source_id}_page_{n} or {source_id}_chunk_{n}
            if document.name.split('/')[-1].startswith(source_id):
                try:
                    delete_request = discoveryengine.DeleteDocumentRequest(
                        name=document.name
                    )
                    client.delete_document(request=delete_request)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete chunk document {document.name}: {e}")
        
        logger.info(f"Deleted {deleted_count} chunk documents for {source_id}")
        
    except Exception as e:
        logger.error(f"Error listing/deleting chunks: {e}")
        raise
    
    return deleted_count


def delete_indexed_summary(source_id: str) -> bool:
    """
    Delete indexed summary for a source from Discovery Engine.
    
    Args:
        source_id: The source_id whose summary to delete
        
    Returns:
        True if deleted, False if not found
    """
    client = discoveryengine.DocumentServiceClient()
    
    # Summary document ID is the source_id itself
    document_name = (
        f"projects/{PROJECT_ID}/"
        f"locations/{VERTEX_SEARCH_LOCATION}/"
        f"collections/default_collection/"
        f"dataStores/{SUMMARIES_DATASTORE_ID}/"
        f"branches/default_branch/"
        f"documents/{source_id}"
    )
    
    try:
        request = discoveryengine.DeleteDocumentRequest(
            name=document_name
        )
        client.delete_document(request=request)
        logger.info(f"Deleted summary document for {source_id}")
        return True
        
    except Exception as e:
        if "NOT_FOUND" in str(e) or "404" in str(e):
            logger.warning(f"Summary document not found for {source_id}")
            return True  # Consider success if already gone
        else:
            logger.error(f"Error deleting summary: {e}")
            raise
