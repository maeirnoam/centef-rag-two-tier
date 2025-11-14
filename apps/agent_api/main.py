"""
FastAPI application for CENTEF RAG Agent API.
Provides endpoints for manifest management and document retrieval.
"""
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, status, Depends, UploadFile, File, BackgroundTasks
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
from shared.auth import get_current_user, get_optional_user, User, create_access_token, require_role
from shared.chat_history import (
    ChatMessage,
    ConversationSession,
    MessageRole,
    save_message,
    get_conversation_history,
    get_user_sessions,
    get_session_metadata,
    create_new_session,
    delete_session,
    update_session_title
)
from shared.user_management import (
    create_user,
    authenticate_user,
    get_user_by_id,
    get_user_by_email,
    list_all_users,
    increment_user_tokens,
    update_user_password,
    deactivate_user,
    hash_password,
    update_user
)
from apps.agent_api.retriever_vertex_search import search_two_tier
from apps.agent_api.synthesizer import synthesize_answer

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


# ============================================================================
# Background Processing Functions
# ============================================================================

def process_uploaded_document(source_id: str, source_uri: str, mimetype: str):
    """
    Background task to process uploaded document to pending_approval status:
    1. Extract chunks (PDF/DOCX/Image/SRT)
    2. Summarize chunks with Gemini and extract metadata
    3. Stop at pending_approval for admin review
    
    Note: Indexing to Discovery Engine happens separately after admin approval.
    
    Args:
        source_id: Document source ID
        source_uri: GCS URI of uploaded file
        mimetype: File MIME type
    """
    import time
    logger.info(f"Starting background processing for {source_id}")

    # Add a small delay to ensure manifest entry is fully written
    # This helps avoid race conditions when multiple files are uploaded quickly
    time.sleep(2)

    try:
        # Import processing functions
        from tools.processing.process_pdf import process_pdf
        from tools.processing.process_docx import process_docx
        from tools.processing.process_image import process_image
        from tools.processing.process_srt import process_srt
        from tools.processing.summarize_chunks import summarize_chunks

        # Verify manifest entry exists before processing
        max_retries = 3
        for attempt in range(max_retries):
            try:
                from shared.manifest import get_manifest_entry
                entry = get_manifest_entry(source_id)
                if entry:
                    logger.info(f"Manifest entry confirmed for {source_id}")
                    break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Manifest entry not found for {source_id}, retrying... (attempt {attempt+1}/{max_retries})")
                    time.sleep(2)
                else:
                    logger.error(f"Manifest entry not found for {source_id} after {max_retries} attempts")
                    raise

        # Step 1: Process to chunks based on file type
        logger.info(f"[1/2] Processing {source_id} to chunks...")
        
        if mimetype == 'application/pdf':
            chunks_path = process_pdf(source_id, source_uri)
        elif mimetype in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
            chunks_path = process_docx(source_id, source_uri)
        elif mimetype in ['image/png', 'image/jpeg']:
            chunks_path = process_image(source_id, source_uri)
        elif mimetype == 'application/x-subrip':
            chunks_path = process_srt(source_id, source_uri)
        else:
            raise ValueError(f"Unsupported mimetype: {mimetype}")
        
        logger.info(f"Chunks created at {chunks_path}")
        
        # Step 2: Summarize chunks and extract metadata
        logger.info(f"[2/2] Summarizing {source_id} and extracting metadata...")
        summary_path = summarize_chunks(source_id)
        logger.info(f"Summary created at {summary_path}")
        
        # Document is now ready for admin approval
        # Status should be pending_approval (set by summarize_and_upload)
        logger.info(f"✅ Background processing complete for {source_id} - Ready for admin approval")
        
    except Exception as e:
        logger.error(f"❌ Background processing failed for {source_id}: {e}", exc_info=True)
        # Update manifest status to error
        try:
            update_manifest_entry(source_id, {
                "status": DocumentStatus.ERROR,
                "notes": f"Processing error: {str(e)}"
            })
        except Exception as update_error:
            logger.error(f"Failed to update manifest entry for {source_id}: {update_error}")


# ============================================================================
# Pydantic Models
# ============================================================================
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


@app.get("/manifest/{source_id}/summary")
def get_summary(source_id: str):
    """
    Get the summary text for a document by fetching from GCS.

    Args:
        source_id: The source_id to retrieve summary for

    Returns:
        JSON with summary_text field
    """
    logger.info(f"GET /manifest/{source_id}/summary")

    try:
        from google.cloud import storage
        import json

        entry = get_manifest_entry(source_id)

        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manifest entry not found for source_id={source_id}"
            )

        if not entry.summary_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No summary available for source_id={source_id}"
            )

        # Parse GCS path
        if not entry.summary_path.startswith('gs://'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid summary path format"
            )

        path_without_scheme = entry.summary_path[5:]  # Remove 'gs://'
        bucket_name, blob_path = path_without_scheme.split('/', 1)

        # Fetch from GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        if not blob.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Summary file not found in GCS"
            )

        content = blob.download_as_text()

        # Parse JSONL and extract summary_text
        lines = content.strip().split('\n')
        for line in lines:
            try:
                data = json.loads(line)
                if 'summary_text' in data:
                    return {"summary_text": data['summary_text']}
            except json.JSONDecodeError:
                continue

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No summary_text found in summary file"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting summary: {str(e)}"
        )


@app.put("/manifest/{source_id}", response_model=ManifestEntryResponse)
def update_manifest(source_id: str, update_request: ManifestUpdateRequest):
    """
    Update a manifest entry.

    NOTE: Changing 'approved' status requires admin role. Use /admin/manifest/{source_id}/approve endpoint.
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
        
        # Prevent approval changes through this endpoint
        if "approved" in patch:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Use /admin/manifest/{source_id}/approve endpoint to change approval status (admin only)"
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


# ============================================================================
# File Upload Endpoint
# ============================================================================

@app.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a document file to GCS and create manifest entry.
    Automatically triggers processing pipeline in background.
    
    Supports: PDF, DOCX, DOC, PNG, JPG, JPEG, SRT
    
    Args:
        background_tasks: FastAPI background tasks
        file: Uploaded file
        current_user: Authenticated user
    
    Returns:
        Created manifest entry
    """
    logger.info(f"POST /upload file={file.filename} by user={current_user.user_id}")
    
    # Validate file type
    allowed_extensions = {'.pdf', '.docx', '.doc', '.png', '.jpg', '.jpeg', '.srt'}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Determine mimetype
    mimetype_map = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.srt': 'application/x-subrip'
    }
    mimetype = mimetype_map.get(file_ext, 'application/octet-stream')
    
    try:
        # Generate source_id - sanitize to match Discovery Engine pattern [a-zA-Z0-9-_]*
        filename_stem = Path(file.filename).stem
        # Replace spaces and invalid chars with underscores
        sanitized_stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in filename_stem)
        source_id = f"{sanitized_stem}_{uuid.uuid4().hex[:8]}"
        
        # Get GCS paths from environment
        source_bucket = os.getenv("SOURCE_BUCKET", "centef-rag-bucket")
        
        # Upload to GCS
        from google.cloud import storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(source_bucket)
        
        # Upload to gs://{bucket}/sources/{filename} (matches existing convention)
        blob_path = f"sources/{file.filename}"
        blob = bucket.blob(blob_path)
        
        # Read and upload file content
        contents = await file.read()
        blob.upload_from_string(contents, content_type=mimetype)
        
        source_uri = f"gs://{source_bucket}/{blob_path}"
        logger.info(f"File uploaded to: {source_uri}")
        
        # Create manifest entry
        entry = ManifestEntry(
            source_id=source_id,
            filename=file.filename,
            title=Path(file.filename).stem.replace('_', ' ').title(),
            mimetype=mimetype,
            source_uri=source_uri,
            ingested_by=current_user.email,
            notes=f"Uploaded via web interface by {current_user.email}",
            status=DocumentStatus.PENDING_PROCESSING
        )
        
        created_entry = create_manifest_entry(entry)
        
        # Trigger background processing
        background_tasks.add_task(
            process_uploaded_document,
            source_id=source_id,
            source_uri=source_uri,
            mimetype=mimetype
        )
        logger.info(f"Queued background processing for {source_id}")
        
        return {
            "source_id": source_id,
            "filename": file.filename,
            "source_uri": source_uri,
            "status": "pending_processing",
            "message": "File uploaded successfully. Processing started in background."
        }
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )


# ============================================================================
# Admin Endpoints (Require admin role)
# ============================================================================

@app.get("/admin/manifest/pending", response_model=List[ManifestEntryResponse])
async def get_pending_approvals(current_user: User = Depends(require_role("admin"))):
    """
    Get all documents pending approval (admin only).
    
    Args:
        current_user: Authenticated admin user
    
    Returns:
        List of documents with status=pending_approval
    """
    logger.info(f"GET /admin/manifest/pending by admin={current_user.user_id}")
    
    try:
        entries = get_manifest_entries(status="pending_approval")
        
        response = [
            ManifestEntryResponse(**entry.to_dict())
            for entry in entries
        ]
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting pending approvals: {str(e)}"
        )


class ApprovalRequest(BaseModel):
    """Request model for document approval."""
    approved: bool
    notes: Optional[str] = None


@app.put("/admin/manifest/{source_id}/approve", response_model=ManifestEntryResponse)
async def approve_document(
    source_id: str,
    approval: ApprovalRequest,
    current_user: User = Depends(require_role("admin"))
):
    """
    Approve or reject a document (admin only).
    
    When approved=True and status=pending_approval, automatically changes status to pending_embedding.
    
    Args:
        source_id: The source_id to approve/reject
        approval: Approval decision and optional notes
        current_user: Authenticated admin user
    
    Returns:
        Updated manifest entry
    """
    logger.info(f"PUT /admin/manifest/{source_id}/approve by admin={current_user.user_id}, approved={approval.approved}")
    
    try:
        # Get current entry
        entry = get_manifest_entry(source_id)
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manifest entry not found for source_id={source_id}"
            )
        
        # Build update patch
        patch = {
            "approved": approval.approved
        }
        
        if approval.notes:
            patch["notes"] = approval.notes
        
        # If approving a pending_approval document, move to pending_embedding
        if approval.approved and entry.status == "pending_approval":
            patch["status"] = "pending_embedding"
            logger.info(f"Document approved, moving to pending_embedding: {source_id}")
        
        # Update entry
        updated_entry = update_manifest_entry(source_id, patch)
        
        return ManifestEntryResponse(**updated_entry.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving document: {str(e)}"
        )


@app.get("/admin/stats")
async def get_admin_stats(current_user: User = Depends(require_role("admin"))):
    """
    Get system statistics (admin only).
    
    Args:
        current_user: Authenticated admin user
    
    Returns:
        System statistics
    """
    logger.info(f"GET /admin/stats by admin={current_user.user_id}")
    
    try:
        # Get manifest stats
        all_entries = get_manifest_entries()
        status_counts = {}
        for entry in all_entries:
            status_counts[entry.status] = status_counts.get(entry.status, 0) + 1
        
        # Get user stats
        all_users = list_all_users()
        active_users = sum(1 for u in all_users if u.is_active)
        admin_users = sum(1 for u in all_users if "admin" in u.roles)
        
        return {
            "documents": {
                "total": len(all_entries),
                "by_status": status_counts,
                "pending_approval": status_counts.get("pending_approval", 0)
            },
            "users": {
                "total": len(all_users),
                "active": active_users,
                "admins": admin_users
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting admin stats: {str(e)}"
        )


@app.get("/admin/users", response_model=List[Dict[str, Any]])
async def list_users_admin(current_user: User = Depends(require_role("admin"))):
    """
    List all users (admin only).
    
    Args:
        current_user: Authenticated admin user
    
    Returns:
        List of all users (passwords excluded)
    """
    logger.info(f"GET /admin/users by admin={current_user.user_id}")
    
    try:
        users = list_all_users()
        
        # Return user info without passwords
        return [
            {
                "user_id": u.user_id,
                "email": u.email,
                "full_name": u.full_name,
                "roles": u.roles,
                "is_active": u.is_active,
                "created_at": u.created_at,
                "last_login": u.last_login
            }
            for u in users
        ]
        
    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing users: {str(e)}"
        )


@app.delete("/admin/sources/{source_id}")
async def delete_source(
    source_id: str,
    current_user: User = Depends(require_role("admin"))
):
    """
    Delete a source and all associated data (admin only).
    
    This performs cascading deletion of:
    - Source file from GCS
    - Chunks JSONL from GCS  
    - Summary JSONL from GCS
    - All indexed chunk documents from Discovery Engine
    - Indexed summary document from Discovery Engine
    - Manifest entry
    
    Args:
        source_id: The source_id to delete
        current_user: Authenticated admin user
    
    Returns:
        Deletion result with details
    """
    logger.info(f"DELETE /admin/sources/{source_id} by admin={current_user.user_id}")
    
    try:
        from shared.source_management import delete_source_completely
        
        result = delete_source_completely(source_id)
        
        if result["success"]:
            return {
                "message": f"Successfully deleted source {source_id}",
                "deleted": result["deleted"]
            }
        else:
            return {
                "message": f"Partially deleted source {source_id}",
                "deleted": result["deleted"],
                "errors": result["errors"]
            }
        
    except Exception as e:
        logger.error(f"Error deleting source: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting source: {str(e)}"
        )


# ============================================================================
# Admin User Management Endpoints
# ============================================================================

class CreateUserRequest(BaseModel):
    """Request model for creating a user."""
    email: str
    password: str
    full_name: str
    roles: List[str] = Field(default_factory=lambda: ["user"])


class UpdateUserRequest(BaseModel):
    """Request model for updating a user."""
    full_name: Optional[str] = None
    roles: Optional[List[str]] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None  # New password if changing


@app.post("/admin/users", status_code=status.HTTP_201_CREATED)
async def create_user_admin(
    request: CreateUserRequest,
    current_user: User = Depends(require_role("admin"))
):
    """
    Create a new user (admin only).
    
    Args:
        request: User creation details
        current_user: Authenticated admin user
    
    Returns:
        Created user information (without password)
    """
    logger.info(f"POST /admin/users by admin={current_user.user_id}, email={request.email}")
    
    try:
        user = create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            roles=request.roles
        )
        
        return {
            "message": "User created successfully",
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "full_name": user.full_name,
                "roles": user.roles,
                "is_active": user.is_active,
                "created_at": user.created_at
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )


@app.put("/admin/users/{user_id}")
async def update_user_admin(
    user_id: str,
    request: UpdateUserRequest,
    current_user: User = Depends(require_role("admin"))
):
    """
    Update a user (admin only).
    
    Can update:
    - Full name
    - Roles
    - Active status
    - Password
    
    Args:
        user_id: User ID to update
        request: Update fields
        current_user: Authenticated admin user
    
    Returns:
        Updated user information
    """
    logger.info(f"PUT /admin/users/{user_id} by admin={current_user.user_id}")
    
    try:
        # Get existing user
        user = get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}"
            )
        
        # Update fields
        updated = False
        
        if request.full_name is not None:
            user.full_name = request.full_name
            updated = True
        
        if request.roles is not None:
            user.roles = request.roles
            updated = True
        
        if request.is_active is not None:
            user.is_active = request.is_active
            updated = True
        
        if request.password is not None:
            # Update password separately
            update_user_password(user_id, request.password)
            updated = True
        
        # Save user if any non-password fields were updated
        if updated and request.password is None:
            update_user(user)
        
        logger.info(f"User {user_id} updated successfully")
        
        return {
            "message": "User updated successfully",
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "full_name": user.full_name,
                "roles": user.roles,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "last_login": user.last_login,
                "total_tokens": user.total_tokens
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )


@app.delete("/admin/users/{user_id}")
async def delete_user_admin(
    user_id: str,
    current_user: User = Depends(require_role("admin"))
):
    """
    Delete (deactivate) a user (admin only).
    
    This performs soft delete by setting is_active=False.
    
    Args:
        user_id: User ID to delete
        current_user: Authenticated admin user
    
    Returns:
        Deletion confirmation
    """
    logger.info(f"DELETE /admin/users/{user_id} by admin={current_user.user_id}")
    
    try:
        # Prevent self-deletion
        if user_id == current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Get user to confirm existence
        user = get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}"
            )
        
        # Deactivate user
        success = deactivate_user(user_id)
        
        if success:
            return {
                "message": f"User {user_id} deactivated successfully",
                "user_id": user_id,
                "email": user.email
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate user"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )


# ============================================================================
# Authentication Endpoints
# ============================================================================

class RegisterRequest(BaseModel):
    """Request model for user registration."""
    email: str
    password: str
    full_name: str


class LoginRequest(BaseModel):
    """Request model for user login."""
    email: str
    password: str


class TokenResponse(BaseModel):
    """Response model for authentication token."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


@app.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    Register a new user.
    
    Args:
        request: Registration details (email, password, full_name)
    
    Returns:
        JWT access token
    """
    logger.info(f"POST /auth/register for email={request.email}")
    
    try:
        # Create user
        user = create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name
        )
        
        # Generate JWT token
        token = create_access_token({"sub": user.user_id, "email": user.email})
        
        return TokenResponse(
            access_token=token,
            user_id=user.user_id,
            email=user.email
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error registering user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering user: {str(e)}"
        )


@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Login with email and password.
    
    Args:
        request: Login credentials (email, password)
    
    Returns:
        JWT access token
    """
    logger.info(f"POST /auth/login for email={request.email}")
    
    try:
        # Authenticate user
        user = authenticate_user(request.email, request.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Generate JWT token
        token = create_access_token({"sub": user.user_id, "email": user.email})
        
        return TokenResponse(
            access_token=token,
            user_id=user.user_id,
            email=user.email
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during login: {str(e)}"
        )


@app.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information.
    
    Args:
        current_user: Authenticated user
    
    Returns:
        User information
    """
    logger.info(f"GET /auth/me for user={current_user.user_id}")
    
    # Get full user profile
    user_profile = get_user_by_id(current_user.user_id)
    
    if not user_profile:
        # User authenticated via API key or doesn't have profile
        return {
            "user_id": current_user.user_id,
            "email": current_user.email,
            "roles": current_user.roles
        }
    
    return {
        "user_id": user_profile.user_id,
        "email": user_profile.email,
        "full_name": user_profile.full_name,
        "roles": user_profile.roles,
        "created_at": user_profile.created_at,
        "last_login": user_profile.last_login
    }


# ============================================================================
# Chat & Query Endpoints
# ============================================================================

class ChatRequest(BaseModel):
    """Request model for chat."""
    query: str
    session_id: Optional[str] = None  # If None, creates new session
    max_chunks: int = 8
    max_summaries: int = 3
    temperature: float = 0.2


class ChatResponse(BaseModel):
    """Response model for chat."""
    message_id: str
    session_id: str
    answer: str
    sources: List[Dict[str, Any]]
    explicit_citations: List[str]
    model_used: str


class SessionResponse(BaseModel):
    """Response model for conversation session."""
    session_id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class MessageResponse(BaseModel):
    """Response model for chat message."""
    message_id: str
    session_id: str
    role: str
    content: str
    timestamp: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    model_used: Optional[str] = None


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Send a chat message and get an AI response.
    
    This endpoint:
    1. Creates a new session if session_id is not provided
    2. Saves the user's query
    3. Performs two-tier search (summaries + chunks)
    4. Generates an answer with Gemini
    5. Saves the assistant's response
    6. Returns the answer with citations and sources
    
    Args:
        request: Chat request with query and optional session_id
        current_user: Authenticated user
    
    Returns:
        Chat response with answer, sources, and citations
    """
    logger.info(f"POST /chat from user={current_user.user_id}, query={request.query[:100]}")
    
    try:
        # Create or use existing session
        if request.session_id:
            session_id = request.session_id
            # Update title if this is the first message in the session and title is still default
            current_session = get_session_metadata(current_user.user_id, session_id)
            if current_session and current_session.message_count == 0 and (
                current_session.title == "New Conversation" or current_session.title == "New Chat"
            ):
                # Use first 50 chars of query as title
                update_session_title(current_user.user_id, session_id, request.query[:50])
                logger.info(f"Updated session {session_id} title to: {request.query[:50]}")
        else:
            # Create new session with query as title
            session = create_new_session(current_user.user_id, title=request.query[:50])
            session_id = session.session_id
            logger.info(f"Created new session {session_id}")
        
        # Save user message
        import uuid
        user_message_id = str(uuid.uuid4())
        user_message = ChatMessage(
            message_id=user_message_id,
            session_id=session_id,
            user_id=current_user.user_id,
            role=MessageRole.USER,
            content=request.query
        )
        save_message(user_message)
        
        # Perform two-tier search
        logger.info("Performing two-tier search...")
        search_results = search_two_tier(
            request.query,
            max_chunk_results=request.max_chunks,
            max_summary_results=request.max_summaries
        )
        
        # Synthesize answer
        logger.info("Synthesizing answer with Gemini...")
        synthesis_result = synthesize_answer(
            query=request.query,
            summary_results=search_results.get('summaries', []),
            chunk_results=search_results.get('chunks', []),
            temperature=request.temperature
        )
        
        # Extract token usage from synthesis result
        input_tokens = synthesis_result.get('input_tokens')
        output_tokens = synthesis_result.get('output_tokens')
        total_tokens = synthesis_result.get('total_tokens')
        
        # Save assistant message with token tracking
        assistant_message_id = str(uuid.uuid4())
        assistant_message = ChatMessage(
            message_id=assistant_message_id,
            session_id=session_id,
            user_id=current_user.user_id,
            role=MessageRole.ASSISTANT,
            content=synthesis_result['answer'],
            sources=synthesis_result.get('sources', []),
            citations=synthesis_result.get('explicit_citations', []),
            model_used=synthesis_result.get('model_used'),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            query_metadata={
                "max_chunks": request.max_chunks,
                "max_summaries": request.max_summaries,
                "temperature": request.temperature
            }
        )
        save_message(assistant_message)
        
        # Increment user's total token count
        if total_tokens:
            increment_user_tokens(current_user.user_id, total_tokens)
            logger.info(f"Added {total_tokens} tokens to user {current_user.user_id}")
        
        logger.info(f"Chat completed successfully for session {session_id}")
        
        return ChatResponse(
            message_id=assistant_message_id,
            session_id=session_id,
            answer=synthesis_result['answer'],
            sources=synthesis_result.get('sources', []),
            explicit_citations=synthesis_result.get('explicit_citations', []),
            model_used=synthesis_result.get('model_used', 'unknown')
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}"
        )


@app.get("/chat/sessions", response_model=List[SessionResponse])
async def get_sessions(current_user: User = Depends(get_current_user)):
    """
    Get all conversation sessions for the current user.
    
    Args:
        current_user: Authenticated user
    
    Returns:
        List of conversation sessions, sorted by updated_at (newest first)
    """
    logger.info(f"GET /chat/sessions for user={current_user.user_id}")
    
    try:
        sessions = get_user_sessions(current_user.user_id)
        
        return [
            SessionResponse(**session.to_dict())
            for session in sessions
        ]
        
    except Exception as e:
        logger.error(f"Error getting sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sessions: {str(e)}"
        )


@app.get("/chat/history/{session_id}", response_model=List[MessageResponse])
async def get_history(
    session_id: str,
    limit: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get conversation history for a session.
    
    Args:
        session_id: Session ID
        limit: Optional limit on number of messages to return
        current_user: Authenticated user
    
    Returns:
        List of messages in chronological order
    """
    logger.info(f"GET /chat/history/{session_id} for user={current_user.user_id}")
    
    try:
        messages = get_conversation_history(
            current_user.user_id,
            session_id,
            limit=limit
        )
        
        return [
            MessageResponse(
                message_id=msg.message_id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                sources=msg.sources,
                citations=msg.citations,
                model_used=msg.model_used
            )
            for msg in messages
        ]
        
    except Exception as e:
        logger.error(f"Error getting history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting history: {str(e)}"
        )


@app.post("/chat/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    title: str = "New Conversation",
    current_user: User = Depends(get_current_user)
):
    """
    Create a new conversation session.
    
    Args:
        title: Session title
        current_user: Authenticated user
    
    Returns:
        Created session
    """
    logger.info(f"POST /chat/sessions for user={current_user.user_id}")
    
    try:
        session = create_new_session(current_user.user_id, title=title)
        return SessionResponse(**session.to_dict())
        
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating session: {str(e)}"
        )


@app.delete("/chat/sessions/{session_id}")
async def delete_session_endpoint(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a conversation session and all its messages.
    
    Args:
        session_id: Session ID to delete
        current_user: Authenticated user
    
    Returns:
        Success message
    """
    logger.info(f"DELETE /chat/sessions/{session_id} for user={current_user.user_id}")
    
    try:
        success = delete_session(current_user.user_id, session_id)
        
        if success:
            return {"message": "Session deleted successfully", "session_id": session_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting session: {str(e)}"
        )


@app.patch("/chat/sessions/{session_id}/title", response_model=SessionResponse)
async def update_session_title_endpoint(
    session_id: str,
    title: str,
    current_user: User = Depends(get_current_user)
):
    """
    Update the title of a conversation session.
    
    Args:
        session_id: Session ID
        title: New title
        current_user: Authenticated user
    
    Returns:
        Updated session
    """
    logger.info(f"PATCH /chat/sessions/{session_id}/title for user={current_user.user_id}")
    
    try:
        session = update_session_title(current_user.user_id, session_id, title)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        return SessionResponse(**session.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session title: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating session title: {str(e)}"
        )


# ============================================================================
# Legacy Search Endpoint (kept for backwards compatibility)
# ============================================================================

@app.post("/search")
def search_documents(query: str, max_results: int = 10):
    """
    Search documents using Vertex AI Search.
    
    NOTE: Use /chat endpoint for authenticated queries with history.
    This endpoint is for backwards compatibility only.
    
    Args:
        query: Search query
        max_results: Maximum number of results
    
    Returns:
        Search results with chunks and summaries
    """
    logger.info(f"POST /search with query={query}")
    
    try:
        search_results = search_two_tier(
            query,
            max_chunk_results=max_results,
            max_summary_results=3
        )
        
        return {
            "query": query,
            "summaries": search_results.get('summaries', []),
            "chunks": search_results.get('chunks', [])
        }
        
    except Exception as e:
        logger.error(f"Error in search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing search: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8080"))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
