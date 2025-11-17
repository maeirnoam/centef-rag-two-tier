"""
Shared schemas for CENTEF RAG system.
Defines chunk, summary, and conversion utilities for Discovery Engine JSONL.
"""
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime

from google.cloud import storage

logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
TARGET_BUCKET = os.getenv("TARGET_BUCKET", "centef-rag-chunks")


def sanitize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Sanitize date strings to handle invalid formats.
    Converts invalid dates like '2006-00-00' to just the year '2006'.
    
    Args:
        date_str: Date string to sanitize
        
    Returns:
        Sanitized date string or None if invalid
    """
    if not date_str:
        return None
    
    # Handle common invalid patterns
    date_str = str(date_str).strip()
    
    # Check for pattern like YYYY-00-00 or YYYY-MM-00
    if '-00' in date_str:
        # Extract just the year
        year = date_str.split('-')[0]
        if year.isdigit() and len(year) == 4:
            return year
        return None
    
    # Check for obviously invalid dates
    try:
        parts = date_str.split('-')
        if len(parts) >= 2:
            year = int(parts[0])
            month = int(parts[1])
            if month < 1 or month > 12:
                # Invalid month, return just year
                return str(year) if 1900 <= year <= 2100 else None
        if len(parts) == 3:
            day = int(parts[2])
            if day < 1 or day > 31:
                # Invalid day, return year-month or just year
                return f"{parts[0]}-{parts[1]}" if 1 <= int(parts[1]) <= 12 else parts[0]
    except (ValueError, IndexError):
        # If parsing fails, return as-is if it looks like a year
        if date_str.isdigit() and len(date_str) == 4:
            return date_str
        return None
    
    return date_str


@dataclass
class ChunkMetadata:
    """File-level metadata for a chunk."""
    id: str
    source_id: str
    filename: str
    title: str
    mimetype: str

    # Optional extracted metadata
    author: Optional[str] = None
    organization: Optional[str] = None
    date: Optional[str] = None
    publisher: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None


@dataclass
class ChunkAnchor:
    """Inner-file anchor information."""
    # For PDFs: page number
    page: Optional[int] = None
    
    # For video/audio/SRT: timestamps
    start_sec: Optional[float] = None
    end_sec: Optional[float] = None
    
    # For DOCX/PPTX: section or slide
    section: Optional[str] = None
    slide: Optional[int] = None


@dataclass
class Chunk:
    """
    Represents a single chunk of processed content.
    Combines file-level metadata with chunk-level anchor and content.
    """
    metadata: ChunkMetadata
    anchor: ChunkAnchor
    content: str
    chunk_index: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSONL serialization."""
        result = {
            "id": self.metadata.id,
            "source_id": self.metadata.source_id,
            "filename": self.metadata.filename,
            "title": self.metadata.title,
            "mimetype": self.metadata.mimetype,
            "content": self.content,
            "chunk_index": self.chunk_index,
        }
        
        # Add optional metadata
        if self.metadata.author:
            result["author"] = self.metadata.author
        if self.metadata.organization:
            result["organization"] = self.metadata.organization
        if self.metadata.date:
            # Sanitize date to handle invalid formats like '2006-00-00'
            sanitized_date = sanitize_date(self.metadata.date)
            if sanitized_date:
                result["date"] = sanitized_date
        if self.metadata.publisher:
            result["publisher"] = self.metadata.publisher
        if self.metadata.tags:
            result["tags"] = self.metadata.tags
        if self.metadata.description:
            result["description"] = self.metadata.description
        
        # Add anchor information
        if self.anchor.page is not None:
            result["page"] = self.anchor.page
        if self.anchor.start_sec is not None:
            result["start_sec"] = self.anchor.start_sec
        if self.anchor.end_sec is not None:
            result["end_sec"] = self.anchor.end_sec
        if self.anchor.section:
            result["section"] = self.anchor.section
        if self.anchor.slide is not None:
            result["slide"] = self.anchor.slide
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        """Create Chunk from dictionary."""
        metadata = ChunkMetadata(
            id=data["id"],
            source_id=data["source_id"],
            filename=data["filename"],
            title=data["title"],
            mimetype=data["mimetype"],
            author=data.get("author"),
            organization=data.get("organization"),
            date=data.get("date"),
            publisher=data.get("publisher"),
            tags=data.get("tags", []),
            description=data.get("description")
        )
        
        anchor = ChunkAnchor(
            page=data.get("page"),
            start_sec=data.get("start_sec"),
            end_sec=data.get("end_sec"),
            section=data.get("section"),
            slide=data.get("slide")
        )
        
        return cls(
            metadata=metadata,
            anchor=anchor,
            content=data["content"],
            chunk_index=data.get("chunk_index", 0)
        )


@dataclass
class Summary:
    """
    Represents a document summary with extracted metadata.
    """
    source_id: str
    filename: str
    title: str
    summary_text: str

    # Extracted metadata
    author: Optional[str] = None
    organization: Optional[str] = None
    date: Optional[str] = None
    publisher: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None

    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSONL serialization."""
        result = {
            "id": self.source_id,
            "source_id": self.source_id,
            "filename": self.filename,
            "title": self.title,
            "summary_text": self.summary_text,
            "created_at": self.created_at,
        }
        
        if self.author:
            result["author"] = self.author
        if self.organization:
            result["organization"] = self.organization
        if self.date:
            # Sanitize date to handle invalid formats like '2006-00-00'
            sanitized_date = sanitize_date(self.date)
            if sanitized_date:
                result["date"] = sanitized_date
        if self.publisher:
            result["publisher"] = self.publisher
        if self.tags:
            result["tags"] = self.tags
        if self.description:
            result["description"] = self.description

        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Summary":
        """Create Summary from dictionary."""
        return cls(
            source_id=data["source_id"],
            filename=data["filename"],
            title=data["title"],
            summary_text=data["summary_text"],
            author=data.get("author"),
            organization=data.get("organization"),
            date=data.get("date"),
            publisher=data.get("publisher"),
            tags=data.get("tags", []),
            description=data.get("description"),
            created_at=data.get("created_at", datetime.utcnow().isoformat())
        )


def write_chunks_to_jsonl(chunks: List[Chunk], output_path: str) -> None:
    """
    Write chunks to JSONL file.
    
    Args:
        chunks: List of Chunk objects
        output_path: Path to output JSONL file (can be local or GCS path)
    """
    logger.info(f"Writing {len(chunks)} chunks to {output_path}")
    
    # Handle GCS paths
    if output_path.startswith("gs://"):
        import tempfile
        # Write to temp file first, then upload
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.jsonl', delete=False) as f:
            temp_path = f.name
            for chunk in chunks:
                json.dump(chunk.to_dict(), f, ensure_ascii=False)
                f.write('\n')
        
        # Upload to GCS
        client = storage.Client(project=PROJECT_ID)
        bucket_name = output_path.replace("gs://", "").split("/")[0]
        blob_path = "/".join(output_path.replace("gs://", "").split("/")[1:])
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(temp_path)
        
        # Clean up temp file
        import os
        os.unlink(temp_path)
    else:
        # Local file
        with open(output_path, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                json.dump(chunk.to_dict(), f, ensure_ascii=False)
                f.write('\n')
    
    logger.info(f"Successfully wrote chunks to {output_path}")


def read_chunks_from_jsonl(input_path: str) -> List[Chunk]:
    """
    Read chunks from JSONL file.
    
    Args:
        input_path: Path to input JSONL file (can be local or GCS path)
    
    Returns:
        List of Chunk objects
    """
    logger.info(f"Reading chunks from {input_path}")
    chunks = []
    
    # TODO: Handle GCS paths using google.cloud.storage
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                chunks.append(Chunk.from_dict(data))
    
    logger.info(f"Successfully read {len(chunks)} chunks from {input_path}")
    return chunks


def write_summary_to_jsonl(summary: Summary, output_path: str) -> None:
    """
    Write summary to JSONL file.
    
    Args:
        summary: Summary object
        output_path: Path to output JSONL file (can be local or GCS path)
    """
    logger.info(f"Writing summary to {output_path}")
    
    # TODO: Handle GCS paths using google.cloud.storage
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary.to_dict(), f, ensure_ascii=False)
        f.write('\n')
    
    logger.info(f"Successfully wrote summary to {output_path}")


def read_summary_from_jsonl(input_path: str) -> Summary:
    """
    Read summary from JSONL file.
    
    Args:
        input_path: Path to input JSONL file (can be local or GCS path)
    
    Returns:
        Summary object
    """
    logger.info(f"Reading summary from {input_path}")
    
    # TODO: Handle GCS paths using google.cloud.storage
    with open(input_path, 'r', encoding='utf-8') as f:
        line = f.readline()
        data = json.loads(line)
        summary = Summary.from_dict(data)
    
    logger.info(f"Successfully read summary from {input_path}")
    return summary


def convert_to_discovery_engine_format(chunk: Chunk) -> Dict[str, Any]:
    """
    Convert a Chunk to Discovery Engine document format.
    For direct API usage (not JSONL import).
    
    Args:
        chunk: Chunk object
    
    Returns:
        Dictionary with 'id' and 'jsonData' for Document creation
    """
    # Return document ID and the data to be stored as json_data
    # The json_data will be accessible as struct_data when querying
    return {
        "id": chunk.metadata.id,
        "jsonData": chunk.to_dict()
    }


def convert_summary_to_discovery_engine_format(summary: Summary) -> Dict[str, Any]:
    """
    Convert a Summary to Discovery Engine document format.
    For direct API usage (not JSONL import).
    
    Args:
        summary: Summary object
    
    Returns:
        Dictionary with 'id' and 'jsonData' for Document creation
    """
    # Return document ID and the data to be stored as json_data
    # The json_data will be accessible as struct_data when querying
    return {
        "id": summary.source_id,
        "jsonData": summary.to_dict()
    }


def download_from_gcs_if_needed(path: str) -> str:
    """
    Download file from GCS to local temp if it's a GCS path.
    
    Args:
        path: Local path or GCS path (gs://bucket/path)
    
    Returns:
        Local file path
    """
    if not path.startswith("gs://"):
        return path
    
    logger.info(f"Downloading {path} from GCS")
    
    # Parse GCS path
    parts = path.replace("gs://", "").split("/", 1)
    bucket_name = parts[0]
    blob_path = parts[1]
    
    # Download to temp
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    
    local_path = f"/tmp/{blob_path.replace('/', '_')}"
    blob.download_to_filename(local_path)
    
    logger.info(f"Downloaded to {local_path}")
    return local_path


def upload_to_gcs_if_needed(local_path: str, gcs_path: str) -> None:
    """
    Upload local file to GCS if gcs_path is a GCS path.
    
    Args:
        local_path: Local file to upload
        gcs_path: Destination GCS path (gs://bucket/path) or local path
    """
    if not gcs_path.startswith("gs://"):
        # It's a local path, just copy if different
        if local_path != gcs_path:
            import shutil
            shutil.copy(local_path, gcs_path)
        return
    
    logger.info(f"Uploading {local_path} to {gcs_path}")
    
    # Parse GCS path
    parts = gcs_path.replace("gs://", "").split("/", 1)
    bucket_name = parts[0]
    blob_path = parts[1]
    
    # Upload
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(local_path)
    
    logger.info(f"Uploaded to {gcs_path}")
