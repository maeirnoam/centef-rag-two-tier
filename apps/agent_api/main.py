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

from fastapi import FastAPI, HTTPException, status, Depends, UploadFile, File, Form, BackgroundTasks
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
    update_session_title,
    update_message_feedback
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
# Optimized versions
from apps.agent_api.retriever_optimized import search_two_tier_optimized, analyze_query_characteristics
from apps.agent_api.synthesizer_optimized import synthesize_answer_optimized

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

def process_video_file(source_id: str, source_uri: str, language: str, translate: str):
    """
    Background task to process video file: extract audio, transcribe, translate, chunk.

    Args:
        source_id: Document source ID
        source_uri: GCS URI of uploaded video file
        language: Source language code (e.g., "ar-SA")
        translate: Target language for translation (e.g., "en")
    """
    import time
    logger.info(f"Starting video processing for {source_id}")
    time.sleep(2)  # Allow manifest entry to be written

    try:
        from tools.processing.ingest_video import process_video
        from tools.processing.extract_audio import extract_audio_from_gcs

        # Extract audio first
        audio_uri = source_uri.replace(".mp4", ".wav").replace(".m4a", ".wav")
        logger.info(f"Extracting audio from {source_uri} to {audio_uri}")
        extract_audio_from_gcs(source_uri, audio_uri)

        # Process video with audio transcription
        process_video(
            video_gcs_uri=source_uri,
            source_id=source_id,
            audio_gcs_uri=audio_uri,
            language_code=language,
            translate_to=translate,
            window_seconds=30.0
        )

        logger.info(f"✅ Video processing complete for {source_id}")

        # Step 2: Summarize chunks and extract metadata
        logger.info(f"[2/2] Summarizing {source_id} and extracting metadata...")
        from tools.processing.summarize_chunks import summarize_chunks
        summary_path = summarize_chunks(source_id)
        logger.info(f"Summary created at {summary_path}")
        logger.info(f"✅ Video processing pipeline complete - Ready for admin approval")

    except Exception as e:
        logger.error(f"❌ Video processing failed for {source_id}: {e}", exc_info=True)
        try:
            update_manifest_entry(source_id, {
                "status": DocumentStatus.ERROR,
                "notes": f"Video processing error: {str(e)}"
            })
        except Exception as update_error:
            logger.error(f"Failed to update manifest entry for {source_id}: {update_error}")


def process_audio_file(source_id: str, source_uri: str, language: str, translate: str):
    """
    Background task to process audio file: transcribe, translate, chunk.

    Args:
        source_id: Document source ID
        source_uri: GCS URI of uploaded audio file
        language: Source language code (e.g., "ar-SA")
        translate: Target language for translation (e.g., "en")
    """
    import time
    logger.info(f"Starting audio processing for {source_id}")
    time.sleep(2)  # Allow manifest entry to be written

    try:
        from tools.processing.ingest_audio import process_audio

        # Process audio with transcription
        process_audio(
            audio_gcs_uri=source_uri,
            source_id=source_id,
            language_code=language,
            translate_to=translate,
            window_seconds=30.0
        )

        logger.info(f"✅ Audio processing complete for {source_id}")

        # Step 2: Summarize chunks and extract metadata
        logger.info(f"[2/2] Summarizing {source_id} and extracting metadata...")
        from tools.processing.summarize_chunks import summarize_chunks
        summary_path = summarize_chunks(source_id)
        logger.info(f"Summary created at {summary_path}")
        logger.info(f"✅ Audio processing pipeline complete - Ready for admin approval")

    except Exception as e:
        logger.error(f"❌ Audio processing failed for {source_id}: {e}", exc_info=True)
        try:
            update_manifest_entry(source_id, {
                "status": DocumentStatus.ERROR,
                "notes": f"Audio processing error: {str(e)}"
            })
        except Exception as update_error:
            logger.error(f"Failed to update manifest entry for {source_id}: {update_error}")


def process_youtube_video(source_id: str, url: str, language: str, translate: str):
    """
    Background task to process YouTube video: download audio, upload to GCS, transcribe, translate, chunk.

    Args:
        source_id: Document source ID
        url: YouTube video URL
        language: Source language code (e.g., "ar-SA")
        translate: Target language for translation (e.g., "en")
    """
    import time
    logger.info(f"Starting YouTube processing for {source_id}")
    time.sleep(2)  # Allow manifest entry to be written

    try:
        from tools.processing.ingest_youtube import upload_to_gcs, extract_video_id
        from tools.processing.youtube_downloader_client import (
            download_youtube_via_external_service,
            is_external_downloader_configured
        )
        from tools.processing.ingest_video import process_video
        import tempfile
        import os

        vid_id = extract_video_id(url)
        
        # Try external downloader service first (bypasses Cloud Run bot detection)
        wav_local = None
        tmpdir_to_cleanup = None
        
        if is_external_downloader_configured():
            logger.info(f"Using external YouTube downloader service (non-cloud IP)...")
            try:
                wav_local, video_title = download_youtube_via_external_service(url, vid_id)
                logger.info(f"✓ External download successful: {video_title}")
                
                # Update manifest with video title
                update_manifest_entry(source_id, {"title": video_title})
                
            except Exception as ext_error:
                logger.warning(f"External downloader failed: {ext_error}")
                logger.info("Falling back to local download methods...")
                
                # Fallback: Try local download
                from tools.processing.ingest_youtube import download_audio_with_fallback
                tmpdir_obj = tempfile.TemporaryDirectory()
                tmpdir_to_cleanup = tmpdir_obj
                tmpdir = tmpdir_obj.name
                wav_local = download_audio_with_fallback(url, tmpdir)
        else:
            logger.info("External downloader not configured, using local download...")
            from tools.processing.ingest_youtube import download_audio_with_fallback
            logger.info(f"Downloading audio from YouTube: {url}")
            tmpdir_obj = tempfile.TemporaryDirectory()
            tmpdir_to_cleanup = tmpdir_obj
            tmpdir = tmpdir_obj.name
            wav_local = download_audio_with_fallback(url, tmpdir)

        # Upload to GCS
        source_bucket = os.getenv("SOURCE_BUCKET", "centef-rag-bucket").replace("gs://", "").strip("/")
        dest_blob = f"data/youtube_{vid_id}.wav"
        logger.info(f"Uploading audio to GCS...")
        audio_gs = upload_to_gcs(wav_local, source_bucket, dest_blob)
        
        # Clean up temporary directory if we created one
        if tmpdir_to_cleanup:
            tmpdir_to_cleanup.cleanup()

        # Process with video pipeline
        process_video(
            video_gcs_uri=url,
            source_id=source_id,
            audio_gcs_uri=audio_gs,
            language_code=language,
            translate_to=translate,
            window_seconds=30.0
        )

        logger.info(f"✅ YouTube processing complete for {source_id}")

        # Step 2: Summarize chunks and extract metadata
        logger.info(f"[2/2] Summarizing {source_id} and extracting metadata...")
        from tools.processing.summarize_chunks import summarize_chunks
        summary_path = summarize_chunks(source_id)
        logger.info(f"Summary created at {summary_path}")
        logger.info(f"✅ YouTube processing pipeline complete - Ready for admin approval")

    except Exception as e:
        logger.error(f"❌ YouTube processing failed for {source_id}: {e}", exc_info=True)
        try:
            update_manifest_entry(source_id, {
                "status": DocumentStatus.ERROR,
                "notes": f"YouTube processing error: {str(e)}"
            })
        except Exception as update_error:
            logger.error(f"Failed to update manifest entry for {source_id}: {update_error}")


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
    description: Optional[str] = None
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
    description: Optional[str] = None


class ManifestCreateRequest(BaseModel):
    """Request model for creating manifest entry."""
    source_id: str
    filename: str
    title: str
    mimetype: str
    source_uri: str
    ingested_by: str = "frontend"
    notes: str = ""
    description: Optional[str] = None


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
    from tools.processing.youtube_downloader_client import health_check_external_service
    
    youtube_service = health_check_external_service()
    
    return {
        "status": "healthy",
        "external_youtube_downloader": youtube_service
    }


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
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a document file to GCS and create manifest entry.
    Automatically triggers processing pipeline in background.

    Supports: PDF, DOCX, DOC, PNG, JPG, JPEG, SRT

    Args:
        background_tasks: FastAPI background tasks
        file: Uploaded file
        description: Optional description of the document
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
            description=description,
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


@app.post("/upload/video")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form("ar-SA"),
    translate: str = Form("en"),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a video file for transcription and processing.

    The video will be:
    1. Uploaded to GCS
    2. Audio extracted
    3. Transcribed using Speech-to-Text
    4. Translated (if specified)
    5. Chunked into time windows

    Args:
        file: Video file (MP4, M4A, etc.)
        language: Source language code (default: ar-SA for Arabic)
        translate: Target language for translation (default: en for English)
        description: Optional description of the video
        current_user: Authenticated user
    """
    logger.info(f"POST /upload/video file={file.filename} by user={current_user.user_id}")

    # Validate file type
    allowed_extensions = {'.mp4', '.m4a', '.mov', '.avi', '.mkv'}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video file type not supported: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        # Generate source_id
        filename_stem = Path(file.filename).stem
        sanitized_stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in filename_stem)
        source_id = f"video_{sanitized_stem}_{uuid.uuid4().hex[:8]}"

        # Upload to GCS
        source_bucket = os.getenv("SOURCE_BUCKET", "centef-rag-bucket")
        from google.cloud import storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(source_bucket)

        blob_path = f"sources/{file.filename}"
        blob = bucket.blob(blob_path)

        contents = await file.read()
        blob.upload_from_string(contents, content_type="video/mp4")

        source_uri = f"gs://{source_bucket}/{blob_path}"
        logger.info(f"Video uploaded to: {source_uri}")

        # Create manifest entry
        entry = ManifestEntry(
            source_id=source_id,
            filename=file.filename,
            title=Path(file.filename).stem.replace('_', ' ').title(),
            mimetype="video/mp4",
            source_uri=source_uri,
            ingested_by=current_user.email,
            notes=f"Video uploaded via web interface by {current_user.email}. Language: {language}, Translate to: {translate}",
            description=description,
            status=DocumentStatus.PENDING_PROCESSING
        )

        created_entry = create_manifest_entry(entry)

        # Trigger background video processing
        background_tasks.add_task(
            process_video_file,
            source_id=source_id,
            source_uri=source_uri,
            language=language,
            translate=translate
        )
        logger.info(f"Queued video processing for {source_id}")

        return {
            "source_id": source_id,
            "filename": file.filename,
            "source_uri": source_uri,
            "status": "pending_processing",
            "message": "Video uploaded successfully. Transcription and processing started in background."
        }

    except Exception as e:
        logger.error(f"Error uploading video: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading video: {str(e)}"
        )


@app.post("/upload/audio")
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form("ar-SA"),
    translate: str = Form("en"),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Upload an audio file for transcription and processing.

    The audio will be:
    1. Uploaded to GCS
    2. Transcribed using Speech-to-Text
    3. Translated (if specified)
    4. Chunked into time windows

    Args:
        file: Audio file (WAV, MP3, M4A, etc.)
        language: Source language code (default: ar-SA for Arabic)
        translate: Target language for translation (default: en for English)
        description: Optional description of the audio
        current_user: Authenticated user
    """
    logger.info(f"POST /upload/audio file={file.filename} by user={current_user.user_id}")

    # Validate file type
    allowed_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio file type not supported: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        # Generate source_id
        filename_stem = Path(file.filename).stem
        sanitized_stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in filename_stem)
        source_id = f"audio_{sanitized_stem}_{uuid.uuid4().hex[:8]}"

        # Upload to GCS
        source_bucket = os.getenv("SOURCE_BUCKET", "centef-rag-bucket")
        from google.cloud import storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(source_bucket)

        blob_path = f"sources/{file.filename}"
        blob = bucket.blob(blob_path)

        contents = await file.read()
        blob.upload_from_string(contents, content_type="audio/wav")

        source_uri = f"gs://{source_bucket}/{blob_path}"
        logger.info(f"Audio uploaded to: {source_uri}")

        # Create manifest entry
        entry = ManifestEntry(
            source_id=source_id,
            filename=file.filename,
            title=Path(file.filename).stem.replace('_', ' ').title(),
            mimetype="audio/wav",
            source_uri=source_uri,
            ingested_by=current_user.email,
            notes=f"Audio uploaded via web interface by {current_user.email}. Language: {language}, Translate to: {translate}",
            description=description,
            status=DocumentStatus.PENDING_PROCESSING
        )

        created_entry = create_manifest_entry(entry)

        # Trigger background audio processing
        background_tasks.add_task(
            process_audio_file,
            source_id=source_id,
            source_uri=source_uri,
            language=language,
            translate=translate
        )
        logger.info(f"Queued audio processing for {source_id}")

        return {
            "source_id": source_id,
            "filename": file.filename,
            "source_uri": source_uri,
            "status": "pending_processing",
            "message": "Audio uploaded successfully. Transcription and processing started in background."
        }

    except Exception as e:
        logger.error(f"Error uploading audio: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading audio: {str(e)}"
        )


class YouTubeUploadRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")
    language: str = Field(default="ar-SA", description="Source language code")
    translate: str = Field(default="en", description="Target language for translation")
    description: Optional[str] = Field(default=None, description="Optional description of the video")


@app.post("/upload/youtube")
async def upload_youtube(
    request: YouTubeUploadRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Process a YouTube video URL for transcription.

    The YouTube video will be:
    1. Downloaded (audio only)
    2. Uploaded to GCS
    3. Transcribed using Speech-to-Text
    4. Translated (if specified)
    5. Chunked into time windows

    Args:
        request: YouTube upload request with URL and language settings
        current_user: Authenticated user
    """
    logger.info(f"POST /upload/youtube url={request.url} by user={current_user.user_id}")

    try:
        # Extract video ID from URL
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(request.url)

        video_id = None
        if parsed_url.hostname in ("www.youtube.com", "youtube.com"):
            qs = parse_qs(parsed_url.query)
            if "v" in qs:
                video_id = qs["v"][0]
        elif parsed_url.hostname == "youtu.be":
            video_id = parsed_url.path.lstrip('/')

        if not video_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid YouTube URL. Could not extract video ID."
            )

        # Generate source_id
        source_id = f"youtube_{video_id}_{uuid.uuid4().hex[:8]}"

        # Create manifest entry
        entry = ManifestEntry(
            source_id=source_id,
            filename=f"youtube_{video_id}.mp4",
            title=f"YouTube Video {video_id}",
            mimetype="video/youtube",
            source_uri=request.url,
            ingested_by=current_user.email,
            notes=f"YouTube video uploaded via web interface by {current_user.email}. Language: {request.language}, Translate to: {request.translate}",
            description=request.description,
            status=DocumentStatus.PENDING_PROCESSING
        )

        created_entry = create_manifest_entry(entry)

        # Trigger background YouTube processing
        background_tasks.add_task(
            process_youtube_video,
            source_id=source_id,
            url=request.url,
            language=request.language,
            translate=request.translate
        )
        logger.info(f"Queued YouTube processing for {source_id}")

        return {
            "source_id": source_id,
            "url": request.url,
            "video_id": video_id,
            "status": "pending_processing",
            "message": "YouTube video queued for processing. Download and transcription started in background."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing YouTube URL: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing YouTube URL: {str(e)}"
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


# Password reset token storage (in-memory for simplicity, use Redis/DB in production)
password_reset_tokens = {}


class ForgotPasswordRequest(BaseModel):
    """Request model for forgot password."""
    email: str


class ResetPasswordRequest(BaseModel):
    """Request model for reset password."""
    token: str
    new_password: str


@app.post("/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Request a password reset token.

    Args:
        request: Email address for password reset

    Returns:
        Success message with reset token (in development) or confirmation message
    """
    logger.info(f"POST /auth/forgot-password for email={request.email}")

    try:
        # Check if user exists
        user = get_user_by_email(request.email)

        if not user:
            # For security, don't reveal if email exists or not
            return {
                "message": "If an account with that email exists, a password reset link has been sent.",
                "success": True
            }

        # Generate reset token (valid for 1 hour)
        from datetime import timedelta
        import secrets

        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)

        # Store token with user_id and expiration
        password_reset_tokens[reset_token] = {
            "user_id": user.user_id,
            "email": user.email,
            "expires_at": expires_at.isoformat()
        }

        # Send password reset email
        logger.info(f"Password reset token generated for {user.email}: {reset_token}")
        logger.info(f"Reset URL: /reset-password.html?token={reset_token}")

        # Import and send email
        from shared.email_service import send_password_reset_email
        email_sent = send_password_reset_email(
            to_email=user.email,
            reset_token=reset_token,
            user_name=user.full_name
        )

        # Return response
        response_data = {
            "message": "If an account with that email exists, a password reset link has been sent.",
            "success": True
        }

        # In development mode (no SendGrid API key), include token for testing
        if not email_sent:
            response_data["dev_reset_token"] = reset_token
            response_data["dev_reset_url"] = f"/reset-password.html?token={reset_token}"
            logger.info("Development mode: Reset link included in response")

        return response_data

    except Exception as e:
        logger.error(f"Error in forgot password: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing password reset request"
        )


@app.post("/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password using a valid token.

    Args:
        request: Reset token and new password

    Returns:
        Success message
    """
    logger.info(f"POST /auth/reset-password with token")

    try:
        # Verify token exists and is not expired
        token_data = password_reset_tokens.get(request.token)

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        # Check if token is expired
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        if datetime.utcnow() > expires_at:
            # Remove expired token
            del password_reset_tokens[request.token]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired. Please request a new one."
            )

        # Validate new password
        if len(request.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )

        # Update password
        user_id = token_data["user_id"]
        update_user_password(user_id, request.new_password)

        # Remove used token
        del password_reset_tokens[request.token]

        logger.info(f"Password successfully reset for user {user_id}")

        return {
            "message": "Password successfully reset. You can now login with your new password.",
            "success": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resetting password"
        )


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
    # Optimization flags (enabled by default)
    use_optimizations: bool = True  # Master toggle for all optimizations
    enable_query_expansion: Optional[bool] = None  # Expand query with variations (auto-determined)
    enable_reranking: Optional[bool] = None  # LLM-based relevance reranking (auto-determined)
    enable_deduplication: Optional[bool] = None  # Remove similar/duplicate results (auto-determined)
    enable_adaptive_limits: bool = True  # Dynamically adjust chunk/summary counts based on query
    filter_logic: str = "OR"  # "OR" or "AND" for metadata filters
    metadata_filters: Optional[Dict[str, Any]] = None  # Custom metadata filters


class ChatResponse(BaseModel):
    """Response model for chat."""
    message_id: str
    session_id: str
    answer: str
    sources: List[Dict[str, Any]]
    explicit_citations: List[str]
    follow_up_questions: Optional[List[str]] = None
    model_used: str
    # Optimization metadata
    optimization_metadata: Optional[Dict[str, Any]] = None  # Details about optimizations applied


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
    feedback_rating: Optional[str] = None
    feedback_note: Optional[str] = None
    feedback_timestamp: Optional[str] = None


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
        
        # Initialize optimization metadata
        optimization_metadata = {}
        
        # Perform two-tier search (optimized or standard)
        if request.use_optimizations:
            logger.info("Performing OPTIMIZED two-tier search...")
            
            # Analyze query characteristics if adaptive limits are enabled
            if request.enable_adaptive_limits:
                query_analysis = analyze_query_characteristics(request.query)
                optimization_metadata['query_analysis'] = query_analysis
                logger.info(f"Query analysis: type={query_analysis['query_type']}, complexity={query_analysis['complexity']}, scope={query_analysis['scope']}")
            
            # Call optimized search
            search_results = search_two_tier_optimized(
                query=request.query,
                max_chunk_results=request.max_chunks if not request.enable_adaptive_limits else None,
                max_summary_results=request.max_summaries if not request.enable_adaptive_limits else None,
                enable_query_expansion=request.enable_query_expansion,
                enable_reranking=request.enable_reranking,
                enable_deduplication=request.enable_deduplication,
                use_adaptive_strategy=request.enable_adaptive_limits,
                filter_logic=request.filter_logic
            )
            
            # Extract optimization metadata from search results
            if 'optimizations_applied' in search_results:
                optimization_metadata['search_optimizations'] = search_results['optimizations_applied']
            if 'adaptive_limits' in search_results:
                optimization_metadata['adaptive_limits'] = search_results['adaptive_limits']
            if 'metadata_filters' in search_results:
                optimization_metadata['metadata_filters'] = search_results['metadata_filters']
            
            logger.info(f"Optimized search complete: {len(search_results.get('chunks', []))} chunks, {len(search_results.get('summaries', []))} summaries")
        else:
            logger.info("Performing standard two-tier search...")
            search_results = search_two_tier(
                request.query,
                max_chunk_results=request.max_chunks,
                max_summary_results=request.max_summaries
            )
        
        # Get conversation history for context (up to 50 previous messages)
        conversation_history = get_conversation_history(
            user_id=current_user.user_id,
            session_id=session_id,
            limit=50
        )
        # Exclude the current user message we just saved
        conversation_history = [msg for msg in conversation_history if msg.message_id != user_message_id]
        
        # Synthesize answer (optimized or standard)
        if request.use_optimizations:
            logger.info("Synthesizing answer with OPTIMIZED synthesizer...")
            synthesis_result = synthesize_answer_optimized(
                query=request.query,
                summary_results=search_results.get('summaries', []),
                chunk_results=search_results.get('chunks', []),
                temperature=request.temperature,
                user_id=current_user.user_id,
                session_id=session_id,
                conversation_history=conversation_history
            )
            
            # Extract format detection metadata
            if 'format_info' in synthesis_result:
                optimization_metadata['format_detection'] = synthesis_result['format_info']
            if 'optimizations_applied' in synthesis_result:
                optimization_metadata['synthesis_optimizations'] = synthesis_result['optimizations_applied']
                
            logger.info(f"Optimized synthesis complete with format: {synthesis_result.get('format_info', {}).get('format_type', 'unknown')}")
        else:
            logger.info("Synthesizing answer with standard synthesizer...")
            synthesis_result = synthesize_answer(
                query=request.query,
                summary_results=search_results.get('summaries', []),
                chunk_results=search_results.get('chunks', []),
                temperature=request.temperature,
                user_id=current_user.user_id,
                session_id=session_id,
                conversation_history=conversation_history
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
            answer=synthesis_result.get('full_answer', synthesis_result['answer']),  # Use full_answer which includes citations section
            sources=synthesis_result.get('sources', []),
            explicit_citations=synthesis_result.get('explicit_citations', []),
            follow_up_questions=synthesis_result.get('follow_up_questions', []),
            model_used=synthesis_result.get('model_used', 'unknown'),
            optimization_metadata=optimization_metadata if request.use_optimizations else None
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
                model_used=msg.model_used,
                feedback_rating=msg.feedback_rating,
                feedback_note=msg.feedback_note,
                feedback_timestamp=msg.feedback_timestamp
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


class MessageFeedbackRequest(BaseModel):
    """Request model for message feedback."""
    feedback_rating: str  # "thumbs_up" or "thumbs_down"
    feedback_note: Optional[str] = None


@app.patch("/chat/messages/{message_id}/feedback")
async def update_message_feedback_endpoint(
    message_id: str,
    session_id: str,
    feedback: MessageFeedbackRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update feedback for a specific message.

    Args:
        message_id: Message ID
        session_id: Session ID (query parameter)
        feedback: Feedback rating and optional note
        current_user: Authenticated user

    Returns:
        Success message
    """
    logger.info(f"PATCH /chat/messages/{message_id}/feedback for user={current_user.user_id}")

    try:
        # Validate feedback_rating
        if feedback.feedback_rating not in ["thumbs_up", "thumbs_down"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="feedback_rating must be 'thumbs_up' or 'thumbs_down'"
            )

        success = update_message_feedback(
            user_id=current_user.user_id,
            session_id=session_id,
            message_id=message_id,
            feedback_rating=feedback.feedback_rating,
            feedback_note=feedback.feedback_note
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message {message_id} not found in session {session_id}"
            )

        return {
            "message": "Feedback updated successfully",
            "message_id": message_id,
            "feedback_rating": feedback.feedback_rating
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating message feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating message feedback: {str(e)}"
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
