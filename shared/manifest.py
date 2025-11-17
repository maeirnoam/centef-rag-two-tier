"""
Manifest management for CENTEF RAG system.
Handles reading, writing, and updating the central manifest.jsonl.
"""
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from google.cloud import storage

logger = logging.getLogger(__name__)

# Read from environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
SOURCE_BUCKET = os.getenv("SOURCE_BUCKET", "centef-rag-bucket")
TARGET_BUCKET = os.getenv("TARGET_BUCKET", "centef-rag-chunks")
MANIFEST_PATH = os.getenv("MANIFEST_PATH", "gs://centef-rag-bucket/manifest/manifest.jsonl")


class DocumentStatus(str, Enum):
    """Allowed document statuses in the manifest."""
    PENDING_PROCESSING = "pending_processing"
    PENDING_SUMMARY = "pending_summary"
    PENDING_APPROVAL = "pending_approval"
    PENDING_EMBEDDING = "pending_embedding"
    EMBEDDED = "embedded"
    ERROR = "error"


@dataclass
class ManifestEntry:
    """
    Represents a single document entry in the manifest.
    Tracks lifecycle, metadata, and storage paths.
    """
    source_id: str
    filename: str
    title: str
    mimetype: str
    source_uri: str
    
    status: str = DocumentStatus.PENDING_PROCESSING
    approved: bool = False
    
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    ingested_by: str = "unknown"  # "frontend" | "drive" | "unknown"
    notes: str = ""
    
    # Extracted metadata (populated during summary phase)
    author: Optional[str] = None
    organization: Optional[str] = None
    date: Optional[str] = None
    publisher: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Storage paths
    data_path: Optional[str] = None
    summary_path: Optional[str] = None
    
    def __post_init__(self):
        """Set default storage paths if not provided."""
        if self.data_path is None:
            self.data_path = f"gs://{TARGET_BUCKET}/data/{self.source_id}.jsonl"
        if self.summary_path is None:
            self.summary_path = f"gs://{TARGET_BUCKET}/summaries/{self.source_id}.jsonl"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSONL serialization."""
        return {
            "source_id": self.source_id,
            "filename": self.filename,
            "title": self.title,
            "mimetype": self.mimetype,
            "source_uri": self.source_uri,
            "status": self.status,
            "approved": self.approved,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "ingested_by": self.ingested_by,
            "notes": self.notes,
            "author": self.author,
            "organization": self.organization,
            "date": self.date,
            "publisher": self.publisher,
            "tags": self.tags,
            "data_path": self.data_path,
            "summary_path": self.summary_path,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ManifestEntry":
        """Create ManifestEntry from dictionary."""
        return cls(
            source_id=data["source_id"],
            filename=data["filename"],
            title=data["title"],
            mimetype=data["mimetype"],
            source_uri=data["source_uri"],
            status=data.get("status", DocumentStatus.PENDING_PROCESSING),
            approved=data.get("approved", False),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            ingested_by=data.get("ingested_by", "unknown"),
            notes=data.get("notes", ""),
            author=data.get("author"),
            organization=data.get("organization"),
            date=data.get("date"),
            publisher=data.get("publisher"),
            tags=data.get("tags", []),
            data_path=data.get("data_path"),
            summary_path=data.get("summary_path"),
        )


def _get_storage_client() -> storage.Client:
    """Get Google Cloud Storage client."""
    return storage.Client(project=PROJECT_ID)


def _parse_gcs_path(gcs_path: str) -> tuple[str, str]:
    """
    Parse GCS path into bucket and blob path.
    
    Args:
        gcs_path: Full GCS path like 'gs://bucket/path/file.jsonl'
    
    Returns:
        Tuple of (bucket_name, blob_path)
    """
    if not gcs_path.startswith("gs://"):
        raise ValueError(f"Invalid GCS path: {gcs_path}")
    
    path_parts = gcs_path.replace("gs://", "").split("/", 1)
    bucket_name = path_parts[0]
    blob_path = path_parts[1] if len(path_parts) > 1 else ""
    
    return bucket_name, blob_path


def _load_manifest_entries() -> List[ManifestEntry]:
    """
    Load all manifest entries from GCS.
    
    Returns:
        List of ManifestEntry objects
    """
    logger.info(f"Loading manifest from {MANIFEST_PATH}")
    
    try:
        client = _get_storage_client()
        bucket_name, blob_path = _parse_gcs_path(MANIFEST_PATH)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        if not blob.exists():
            logger.warning(f"Manifest file does not exist, creating empty manifest")
            return []
        
        content = blob.download_as_text()
        entries = []
        
        for line in content.strip().split('\n'):
            if line.strip():
                data = json.loads(line)
                entries.append(ManifestEntry.from_dict(data))
        
        logger.info(f"Loaded {len(entries)} manifest entries")
        return entries
        
    except Exception as e:
        logger.error(f"Error loading manifest: {e}")
        raise


def _write_manifest_entries(entries: List[ManifestEntry]) -> None:
    """
    Write all manifest entries to GCS.
    
    Args:
        entries: List of ManifestEntry objects
    """
    logger.info(f"Writing {len(entries)} manifest entries to {MANIFEST_PATH}")
    
    import time
    from google.api_core.exceptions import TooManyRequests

    max_retries = 5
    base_delay = 1.0  # Start with 1 second

    for attempt in range(max_retries):
        try:
            client = _get_storage_client()
            bucket_name, blob_path = _parse_gcs_path(MANIFEST_PATH)
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)

            # Convert to JSONL
            lines = []
            for entry in entries:
                lines.append(json.dumps(entry.to_dict(), ensure_ascii=False))

            content = '\n'.join(lines) + '\n'

            # Upload to GCS
            blob.upload_from_string(content, content_type='application/jsonl')

            logger.info(f"Successfully wrote manifest")
            return  # Success, exit the function

        except TooManyRequests as e:
            if attempt < max_retries - 1:
                # Calculate delay with exponential backoff
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Rate limited writing manifest, retrying in {delay}s (attempt {attempt+1}/{max_retries})")
                time.sleep(delay)
            else:
                logger.error(f"Failed to write manifest after {max_retries} attempts due to rate limiting")
                raise
        except Exception as e:
            logger.error(f"Error writing manifest: {e}")
            raise


def get_manifest_entries(status: Optional[str] = None) -> List[ManifestEntry]:
    """
    Get manifest entries, optionally filtered by status.
    
    Args:
        status: Optional status filter (e.g., "pending_approval")
    
    Returns:
        List of ManifestEntry objects
    """
    entries = _load_manifest_entries()
    
    if status is not None:
        entries = [e for e in entries if e.status == status]
        logger.info(f"Filtered to {len(entries)} entries with status={status}")
    
    return entries


def get_manifest_entry(source_id: str) -> Optional[ManifestEntry]:
    """
    Get a single manifest entry by source_id.
    
    Args:
        source_id: The source_id to find
    
    Returns:
        ManifestEntry if found, None otherwise
    """
    entries = _load_manifest_entries()
    
    for entry in entries:
        if entry.source_id == source_id:
            return entry
    
    logger.warning(f"Manifest entry not found for source_id={source_id}")
    return None


def update_manifest_entry(source_id: str, patch: Dict[str, Any]) -> ManifestEntry:
    """
    Update a manifest entry with the given patch.
    
    Args:
        source_id: The source_id to update
        patch: Dictionary of fields to update
    
    Returns:
        Updated ManifestEntry
    
    Raises:
        ValueError: If entry not found
    """
    logger.info(f"Updating manifest entry {source_id} with patch: {patch}")
    
    entries = _load_manifest_entries()
    entry_index = None
    
    for i, entry in enumerate(entries):
        if entry.source_id == source_id:
            entry_index = i
            break
    
    if entry_index is None:
        raise ValueError(f"Manifest entry not found for source_id={source_id}")
    
    # Apply patch
    entry = entries[entry_index]
    entry_dict = entry.to_dict()
    entry_dict.update(patch)
    entry_dict["updated_at"] = datetime.utcnow().isoformat()
    
    # Recreate entry from updated dict
    updated_entry = ManifestEntry.from_dict(entry_dict)
    entries[entry_index] = updated_entry
    
    # Write back to GCS
    _write_manifest_entries(entries)
    
    logger.info(f"Successfully updated manifest entry {source_id}")
    
    # If status changed to pending_embedding, trigger embedding
    if patch.get("status") == DocumentStatus.PENDING_EMBEDDING:
        logger.info(f"Status changed to pending_embedding, triggering embedding for {source_id}")
        trigger_embedding_for_source(updated_entry)
    
    return updated_entry


def create_manifest_entry(entry: ManifestEntry) -> ManifestEntry:
    """
    Create a new manifest entry.
    
    Args:
        entry: ManifestEntry to create
    
    Returns:
        Created ManifestEntry
    
    Raises:
        ValueError: If entry with source_id already exists
    """
    logger.info(f"Creating manifest entry for {entry.source_id}")
    
    entries = _load_manifest_entries()
    
    # Check if entry already exists
    for existing in entries:
        if existing.source_id == entry.source_id:
            raise ValueError(f"Manifest entry already exists for source_id={entry.source_id}")
    
    # Add new entry
    entries.append(entry)
    
    # Write back to GCS
    _write_manifest_entries(entries)
    
    logger.info(f"Successfully created manifest entry {entry.source_id}")
    return entry


def trigger_embedding_for_source(entry: ManifestEntry) -> None:
    """
    Trigger embedding/indexing for a document.
    
    This is called when a manifest entry's status becomes "pending_embedding".
    
    Args:
        entry: ManifestEntry to embed
    """
    logger.info(f"Triggering embedding for source_id={entry.source_id}")
    
    try:
        from services.embedding.index_documents import index_document
        logger.info(f"Calling index_document for {entry.source_id}")
        index_document(entry)  # Pass the full entry object, not just source_id
        logger.info(f"Successfully triggered indexing for {entry.source_id}")
    except ImportError as e:
        logger.error(f"Could not import embedding service: {e}")
    except Exception as e:
        logger.error(f"Error triggering embedding: {e}", exc_info=True)
        # Update manifest to error status
        update_manifest_entry(entry.source_id, {
            "status": DocumentStatus.ERROR,
            "notes": f"Indexing error: {str(e)}"
        })


def delete_manifest_entry(source_id: str) -> bool:
    """
    Delete a manifest entry.
    
    Args:
        source_id: The source_id to delete
        
    Returns:
        True if deleted, False if not found
    """
    logger.info(f"Deleting manifest entry for source_id={source_id}")
    
    # Load all entries
    entries = get_manifest_entries()
    
    # Filter out the entry to delete
    original_count = len(entries)
    entries = [e for e in entries if e.source_id != source_id]
    
    if len(entries) == original_count:
        logger.warning(f"Entry {source_id} not found in manifest")
        return False
    
    # Save updated manifest using existing write function
    _write_manifest_entries(entries)
    
    logger.info(f"Successfully deleted manifest entry {source_id}")
    return True
