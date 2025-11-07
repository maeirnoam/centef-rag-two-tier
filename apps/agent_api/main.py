"""
FastAPI application for CENTEF RAG Agent API.
Provides endpoints for manifest management and document retrieval.
"""
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.manifest import (
    ManifestEntry,
    get_manifest_entries,
    get_manifest_entry,
    update_manifest_entry,
    create_manifest_entry,
    DocumentStatus,
    trigger_embedding_for_source
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="CENTEF RAG Agent API",
    description="API for managing and querying the CENTEF RAG system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response
class ManifestEntryResponse(BaseModel):
    """Response model for manifest entry."""
    source_id: str
    filename: str
    title: str
    mimetype: str
    source_uri: str
    status: str
    approved: bool
    created_at: str
    updated_at: str
    ingested_by: str
    notes: str
    author: Optional[str] = None
    organization: Optional[str] = None
    date: Optional[str] = None
    publisher: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    data_path: Optional[str] = None
    summary_path: Optional[str] = None


class ManifestUpdateRequest(BaseModel):
    """Request model for updating manifest entry."""
    title: Optional[str] = None
    status: Optional[str] = None
    approved: Optional[bool] = None
    notes: Optional[str] = None
    author: Optional[str] = None
    organization: Optional[str] = None
    date: Optional[str] = None
    publisher: Optional[str] = None
    tags: Optional[List[str]] = None


class ManifestCreateRequest(BaseModel):
    """Request model for creating manifest entry."""
    source_id: str
    filename: str
    title: str
    mimetype: str
    source_uri: str
    ingested_by: str = "frontend"
    notes: str = ""


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "CENTEF RAG Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/manifest", response_model=List[ManifestEntryResponse])
def list_manifest_entries(status: Optional[str] = None):
    """
    Get all manifest entries, optionally filtered by status.
    
    Args:
        status: Optional status filter (pending_processing, pending_summary, etc.)
    
    Returns:
        List of manifest entries
    """
    logger.info(f"GET /manifest with status={status}")
    
    try:
        entries = get_manifest_entries(status=status)
        
        # Convert to response model
        response = [
            ManifestEntryResponse(**entry.to_dict())
            for entry in entries
        ]
        
        return response
        
    except Exception as e:
        logger.error(f"Error listing manifest entries: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing manifest entries: {str(e)}"
        )


@app.get("/manifest/{source_id}", response_model=ManifestEntryResponse)
def get_manifest(source_id: str):
    """
    Get a single manifest entry by source_id.
    
    Args:
        source_id: The source_id to retrieve
    
    Returns:
        Manifest entry
    """
    logger.info(f"GET /manifest/{source_id}")
    
    try:
        entry = get_manifest_entry(source_id)
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manifest entry not found for source_id={source_id}"
            )
        
        return ManifestEntryResponse(**entry.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting manifest entry: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting manifest entry: {str(e)}"
        )


@app.put("/manifest/{source_id}", response_model=ManifestEntryResponse)
def update_manifest(source_id: str, update_request: ManifestUpdateRequest):
    """
    Update a manifest entry.
    
    When status is set to "pending_embedding", triggers the embedding pipeline.
    
    Args:
        source_id: The source_id to update
        update_request: Fields to update
    
    Returns:
        Updated manifest entry
    """
    logger.info(f"PUT /manifest/{source_id} with data: {update_request}")
    
    try:
        # Build patch dict (only include non-None fields)
        patch = update_request.model_dump(exclude_none=True)
        
        if not patch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided to update"
            )
        
        # Validate status if provided
        if "status" in patch:
            try:
                DocumentStatus(patch["status"])
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {patch['status']}"
                )
        
        # Update entry (this will also trigger embedding if status = pending_embedding)
        updated_entry = update_manifest_entry(source_id, patch)
        
        return ManifestEntryResponse(**updated_entry.to_dict())
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating manifest entry: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating manifest entry: {str(e)}"
        )


@app.post("/manifest", response_model=ManifestEntryResponse, status_code=status.HTTP_201_CREATED)
def create_manifest(create_request: ManifestCreateRequest):
    """
    Create a new manifest entry.
    
    Args:
        create_request: Manifest entry data
    
    Returns:
        Created manifest entry
    """
    logger.info(f"POST /manifest with data: {create_request}")
    
    try:
        # Create ManifestEntry
        entry = ManifestEntry(
            source_id=create_request.source_id,
            filename=create_request.filename,
            title=create_request.title,
            mimetype=create_request.mimetype,
            source_uri=create_request.source_uri,
            ingested_by=create_request.ingested_by,
            notes=create_request.notes,
            status=DocumentStatus.PENDING_PROCESSING
        )
        
        created_entry = create_manifest_entry(entry)
        
        return ManifestEntryResponse(**created_entry.to_dict())
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating manifest entry: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating manifest entry: {str(e)}"
        )


# TODO: Add search/query endpoints
@app.post("/search")
def search_documents(query: str, max_results: int = 10):
    """
    Search documents using Vertex AI Search.
    
    Args:
        query: Search query
        max_results: Maximum number of results
    
    Returns:
        Search results with chunks and summaries
    """
    logger.info(f"POST /search with query={query}")
    
    # TODO: Implement using retriever_vertex_search.py
    return {
        "query": query,
        "results": [],
        "message": "Search not yet implemented - integrate Vertex AI Search"
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
