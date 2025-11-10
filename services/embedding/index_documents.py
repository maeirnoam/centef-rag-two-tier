"""
Document indexing service for CENTEF RAG system.
Indexes chunks and summaries into Vertex AI Search datastores.
"""
import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from google.cloud import storage
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.protobuf import struct_pb2

# Load environment variables first
load_dotenv()

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


def index_chunks_to_discovery_engine(entry: ManifestEntry) -> Dict[str, Any]:
    """
    Index chunks into Vertex AI Search chunk datastore.
    
    Args:
        entry: ManifestEntry with data_path to chunks
        
    Returns:
        Dict with statistics: {
            "total": int,
            "success": int,
            "failed": int,
            "failed_ids": List[str],
            "errors": List[str]
        }
    """
    logger.info(f"Indexing chunks for source_id={entry.source_id}")
    
    # Download chunks
    local_path = download_from_gcs(entry.data_path)
    chunks = read_chunks_from_jsonl(local_path)
    
    logger.info(f"Read {len(chunks)} chunks from {entry.data_path}")
    
    # Initialize Discovery Engine client
    client = discoveryengine.DocumentServiceClient()
    
    # Build parent path for datastore
    parent = (
        f"projects/{PROJECT_ID}/"
        f"locations/{VERTEX_SEARCH_LOCATION}/"
        f"collections/default_collection/"
        f"dataStores/{CHUNKS_DATASTORE_ID}/"
        f"branches/default_branch"
    )
    
    logger.info(f"Indexing to datastore: {parent}")
    
    # Convert chunks to Discovery Engine format and create documents individually
    logger.info(f"Creating {len(chunks)} documents in Discovery Engine")
    
    # Track results
    stats = {
        "total": len(chunks),
        "success": 0,
        "failed": 0,
        "failed_ids": [],
        "errors": []
    }
    
    for i, chunk in enumerate(chunks):
        try:
            doc_dict = convert_to_discovery_engine_format(chunk)
            doc_id = doc_dict["id"]
            
            # Convert chunk data to protobuf Struct
            # Note: We include the content in struct_data, not as a separate content field
            # This matches the datastore configuration (NO_CONTENT or CONTENT_NOT_REQUIRED)
            struct_data = struct_pb2.Struct()
            struct_data.update(doc_dict.get("jsonData", {}))
            
            # Create Document object with struct_data only (like summaries)
            document = discoveryengine.Document(
                id=doc_id,
                struct_data=struct_data
            )
            
            # Create document request
            request = discoveryengine.CreateDocumentRequest(
                parent=parent,
                document=document,
                document_id=doc_id
            )
            
            # Create the document
            response = client.create_document(request=request)
            stats["success"] += 1
            
            if (i + 1) % 10 == 0:
                logger.info(f"Created {i + 1}/{len(chunks)} documents")
                
        except Exception as e:
            error_msg = f"Failed to create document {doc_id}: {str(e)}"
            logger.warning(error_msg)
            stats["failed"] += 1
            stats["failed_ids"].append(doc_id)
            stats["errors"].append(error_msg)
            continue
    
    logger.info(f"Chunk indexing complete: {stats['success']}/{stats['total']} succeeded, {stats['failed']} failed")
    
    if stats["failed"] > 0:
        logger.warning(f"Failed chunk IDs: {', '.join(stats['failed_ids'])}")
    
    return stats


def index_summaries_to_discovery_engine(entry: ManifestEntry) -> Dict[str, Any]:
    """
    Index summary into Vertex AI Search summary datastore.
    
    Args:
        entry: ManifestEntry with summary_path
        
    Returns:
        Dict with statistics: {
            "success": bool,
            "error": str or None
        }
    """
    logger.info(f"Indexing summary for source_id={entry.source_id}")
    
    # Download summary
    local_path = download_from_gcs(entry.summary_path)
    summary = read_summary_from_jsonl(local_path)
    
    logger.info(f"Read summary from {entry.summary_path}")
    
    # Initialize Discovery Engine client
    client = discoveryengine.DocumentServiceClient()
    
    # Build parent path for datastore
    parent = (
        f"projects/{PROJECT_ID}/"
        f"locations/{VERTEX_SEARCH_LOCATION}/"
        f"collections/default_collection/"
        f"dataStores/{SUMMARIES_DATASTORE_ID}/"
        f"branches/default_branch"
    )
    
    logger.info(f"Indexing to datastore: {parent}")
    
    # Convert summary to Discovery Engine format and create document
    logger.info(f"Creating summary document in Discovery Engine")
    
    stats = {"success": False, "error": None}
    
    try:
        doc_dict = convert_summary_to_discovery_engine_format(summary)
        
        # Get the JSON data
        json_content = doc_dict.get("jsonData", doc_dict.get("content", {}))
        logger.info(f"JSON content type: {type(json_content)}")
        logger.info(f"JSON content keys: {json_content.keys() if isinstance(json_content, dict) else 'not a dict'}")
        
        # Convert to protobuf Struct
        struct_data = struct_pb2.Struct()
        struct_data.update(json_content)
        
        # Create Document object with struct_data
        document = discoveryengine.Document(
            id=doc_dict["id"],
            struct_data=struct_data,
        )
        
        # Create document request
        request = discoveryengine.CreateDocumentRequest(
            parent=parent,
            document=document,
            document_id=doc_dict["id"]
        )
        
        # Create the document
        response = client.create_document(request=request)
        logger.info(f"Successfully indexed summary")
        stats["success"] = True
        
    except Exception as e:
        error_msg = f"Failed to create summary document: {str(e)}"
        logger.error(error_msg)
        stats["error"] = error_msg
    
    return stats


def index_document(entry: ManifestEntry) -> Dict[str, Any]:
    """
    Index both chunks and summary for a document.
    
    Args:
        entry: ManifestEntry to index
        
    Returns:
        Dict with indexing results: {
            "source_id": str,
            "success": bool,
            "chunks": {...},
            "summary": {...},
            "error": str or None
        }
    """
    logger.info(f"Starting document indexing for source_id={entry.source_id}")
    
    result = {
        "source_id": entry.source_id,
        "success": False,
        "chunks": None,
        "summary": None,
        "error": None
    }
    
    try:
        # Validate status
        if entry.status != DocumentStatus.PENDING_EMBEDDING:
            logger.warning(
                f"Entry status is {entry.status}, expected {DocumentStatus.PENDING_EMBEDDING}. "
                f"Continuing anyway."
            )
        
        # Index chunks
        if entry.data_path:
            chunks_stats = index_chunks_to_discovery_engine(entry)
            result["chunks"] = chunks_stats
        else:
            logger.warning(f"No data_path found for {entry.source_id}, skipping chunk indexing")
        
        # Index summary
        if entry.summary_path:
            summary_stats = index_summaries_to_discovery_engine(entry)
            result["summary"] = summary_stats
        else:
            logger.warning(f"No summary_path found for {entry.source_id}, skipping summary indexing")
        
        # Determine overall success
        chunks_ok = not result["chunks"] or result["chunks"]["failed"] == 0
        summary_ok = not result["summary"] or result["summary"]["success"]
        
        if chunks_ok and summary_ok:
            # Update manifest status to embedded
            update_manifest_entry(entry.source_id, {
                "status": DocumentStatus.EMBEDDED
            })
            result["success"] = True
            logger.info(f"Successfully indexed document {entry.source_id} and updated status to {DocumentStatus.EMBEDDED}")
        else:
            # Partial failure
            error_parts = []
            if result["chunks"] and result["chunks"]["failed"] > 0:
                error_parts.append(f"{result['chunks']['failed']} chunks failed")
            if result["summary"] and not result["summary"]["success"]:
                error_parts.append("summary failed")
            
            error_msg = "Indexing errors: " + ", ".join(error_parts)
            result["error"] = error_msg
            
            update_manifest_entry(entry.source_id, {
                "status": DocumentStatus.ERROR,
                "notes": error_msg
            })
            
            logger.error(f"Partial failure for {entry.source_id}: {error_msg}")
        
    except Exception as e:
        error_msg = f"Indexing error: {str(e)}"
        result["error"] = error_msg
        logger.error(f"Error indexing document {entry.source_id}: {e}", exc_info=True)
        
        # Update manifest to error status
        update_manifest_entry(entry.source_id, {
            "status": DocumentStatus.ERROR,
            "notes": error_msg
        })
    
    return result


def main():
    """CLI entry point for testing."""
    from shared.manifest import get_manifest_entry, get_manifest_entries
    
    parser = argparse.ArgumentParser(description="Index document into Discovery Engine")
    parser.add_argument("--source-id", help="Source ID from manifest (omit to index all pending)")
    parser.add_argument("--chunks-only", action="store_true", help="Only index chunks")
    parser.add_argument("--summaries-only", action="store_true", help="Only index summaries")
    
    args = parser.parse_args()
    
    try:
        if args.source_id:
            # Index single document
            entry = get_manifest_entry(args.source_id)
            if not entry:
                logger.error(f"Manifest entry not found for source_id={args.source_id}")
                return 1
            
            # Apply filters
            if args.chunks_only:
                entry.summary_path = None
            elif args.summaries_only:
                entry.data_path = None
            
            result = index_document(entry)
            
            print()
            print("="*80)
            print(f"INDEXING RESULTS FOR {result['source_id']}")
            print("="*80)
            
            if result["chunks"]:
                print(f"\nChunks: {result['chunks']['success']}/{result['chunks']['total']} succeeded")
                if result['chunks']['failed'] > 0:
                    print(f"  Failed: {result['chunks']['failed']}")
                    print(f"  Failed IDs: {', '.join(result['chunks']['failed_ids'][:5])}" + 
                          (" ..." if len(result['chunks']['failed_ids']) > 5 else ""))
            
            if result["summary"]:
                status = "✅ Success" if result['summary']['success'] else "❌ Failed"
                print(f"\nSummary: {status}")
                if result['summary']['error']:
                    print(f"  Error: {result['summary']['error']}")
            
            if result["success"]:
                print(f"\n✅ Overall: SUCCESS")
            else:
                print(f"\n❌ Overall: FAILED")
                if result["error"]:
                    print(f"  Error: {result['error']}")
            
            print("="*80)
            
            return 0 if result["success"] else 1
        
        else:
            # Index all pending documents
            entries = get_manifest_entries()
            pending = [e for e in entries if e.status == DocumentStatus.PENDING_EMBEDDING]
            
            if not pending:
                print("No pending documents to index.")
                return 0
            
            print(f"Found {len(pending)} pending documents to index")
            print()
            
            results = []
            for entry in pending:
                # Apply filters
                if args.chunks_only:
                    entry.summary_path = None
                elif args.summaries_only:
                    entry.data_path = None
                
                result = index_document(entry)
                results.append(result)
            
            # Print summary
            print()
            print("="*80)
            print("INDEXING SUMMARY")
            print("="*80)
            
            successful = [r for r in results if r["success"]]
            failed = [r for r in results if not r["success"]]
            
            print(f"\nTotal documents: {len(results)}")
            print(f"✅ Successful: {len(successful)}")
            print(f"❌ Failed: {len(failed)}")
            
            if failed:
                print("\nFailed source_ids:")
                for r in failed:
                    print(f"  - {r['source_id']}: {r['error']}")
            
            # Chunk stats
            total_chunks = sum(r["chunks"]["total"] for r in results if r["chunks"])
            success_chunks = sum(r["chunks"]["success"] for r in results if r["chunks"])
            failed_chunks = sum(r["chunks"]["failed"] for r in results if r["chunks"])
            
            if total_chunks > 0:
                print(f"\nChunk statistics:")
                print(f"  Total: {total_chunks}")
                print(f"  Success: {success_chunks}")
                print(f"  Failed: {failed_chunks}")
            
            # Summary stats
            total_summaries = sum(1 for r in results if r["summary"])
            success_summaries = sum(1 for r in results if r["summary"] and r["summary"]["success"])
            
            if total_summaries > 0:
                print(f"\nSummary statistics:")
                print(f"  Total: {total_summaries}")
                print(f"  Success: {success_summaries}")
                print(f"  Failed: {total_summaries - success_summaries}")
            
            print("="*80)
            
            return 0 if len(failed) == 0 else 1
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
