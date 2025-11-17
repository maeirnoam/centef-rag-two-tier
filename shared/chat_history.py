"""
Chat history management for CENTEF RAG system.
Handles storing and retrieving conversation history per user.
"""
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from google.cloud import storage

logger = logging.getLogger(__name__)

# Read from environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
CHAT_HISTORY_BUCKET = os.getenv("CHAT_HISTORY_BUCKET", "centef-rag-bucket")
CHAT_HISTORY_PATH = os.getenv("CHAT_HISTORY_PATH", "chat_history")


class MessageRole(str, Enum):
    """Message roles in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class ChatMessage:
    """
    Represents a single message in a conversation.
    """
    message_id: str
    session_id: str
    user_id: str
    role: str  # MessageRole
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Optional metadata for assistant responses
    sources: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    model_used: Optional[str] = None
    
    # Token usage tracking
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    
    # Query metadata
    query_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSONL serialization."""
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "sources": self.sources,
            "citations": self.citations,
            "model_used": self.model_used,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "query_metadata": self.query_metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        """Create ChatMessage from dictionary."""
        return cls(
            message_id=data["message_id"],
            session_id=data["session_id"],
            user_id=data["user_id"],
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
            sources=data.get("sources", []),
            citations=data.get("citations", []),
            model_used=data.get("model_used"),
            input_tokens=data.get("input_tokens"),
            output_tokens=data.get("output_tokens"),
            total_tokens=data.get("total_tokens"),
            query_metadata=data.get("query_metadata", {}),
        )


@dataclass
class ConversationSession:
    """
    Represents a conversation session metadata.
    """
    session_id: str
    user_id: str
    title: str  # Auto-generated from first message or user-set
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    message_count: int = 0
    total_tokens: int = 0  # Total tokens used in this session
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": self.message_count,
            "total_tokens": self.total_tokens,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationSession":
        """Create ConversationSession from dictionary."""
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            title=data["title"],
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            message_count=data.get("message_count", 0),
            total_tokens=data.get("total_tokens", 0),
        )


def _get_storage_client() -> storage.Client:
    """Get Google Cloud Storage client."""
    return storage.Client(project=PROJECT_ID)


def _parse_gcs_path(gcs_path: str) -> tuple[str, str]:
    """
    Parse GCS path into bucket and blob path.
    
    Args:
        gcs_path: GCS path (gs://bucket/path)
    
    Returns:
        Tuple of (bucket_name, blob_path)
    """
    if gcs_path.startswith("gs://"):
        gcs_path = gcs_path[5:]
    parts = gcs_path.split("/", 1)
    bucket_name = parts[0]
    blob_path = parts[1] if len(parts) > 1 else ""
    return bucket_name, blob_path


def save_message(message: ChatMessage) -> None:
    """
    Save a chat message to GCS.
    Messages are stored in: gs://{bucket}/chat_history/{user_id}/{session_id}.jsonl
    
    Args:
        message: ChatMessage to save
    """
    logger.info(f"Saving message {message.message_id} for user={message.user_id}, session={message.session_id}")
    
    try:
        client = _get_storage_client()
        bucket = client.bucket(CHAT_HISTORY_BUCKET)
        
        # Path: chat_history/{user_id}/{session_id}.jsonl
        blob_path = f"{CHAT_HISTORY_PATH}/{message.user_id}/{message.session_id}.jsonl"
        blob = bucket.blob(blob_path)
        
        # Append to existing file or create new
        existing_content = ""
        if blob.exists():
            existing_content = blob.download_as_text()
        
        # Append new message as JSONL
        new_line = json.dumps(message.to_dict()) + "\n"
        blob.upload_from_string(existing_content + new_line, content_type="application/jsonl")
        
        logger.info(f"Message saved to gs://{CHAT_HISTORY_BUCKET}/{blob_path}")
        
        # Update session metadata (including token count)
        tokens_to_add = message.total_tokens or 0
        _update_session_metadata(message.user_id, message.session_id, tokens_to_add)
        
    except Exception as e:
        logger.error(f"Error saving message: {e}", exc_info=True)
        raise


def get_conversation_history(
    user_id: str,
    session_id: str,
    limit: Optional[int] = None
) -> List[ChatMessage]:
    """
    Retrieve conversation history for a session.
    
    Args:
        user_id: User ID
        session_id: Session ID
        limit: Optional limit on number of messages to return (most recent)
    
    Returns:
        List of ChatMessage objects in chronological order
    """
    logger.info(f"Retrieving conversation history for user={user_id}, session={session_id}")
    
    try:
        client = _get_storage_client()
        bucket = client.bucket(CHAT_HISTORY_BUCKET)
        
        blob_path = f"{CHAT_HISTORY_PATH}/{user_id}/{session_id}.jsonl"
        blob = bucket.blob(blob_path)
        
        if not blob.exists():
            logger.info(f"No conversation history found at gs://{CHAT_HISTORY_BUCKET}/{blob_path}")
            return []
        
        # Download and parse JSONL
        content = blob.download_as_text()
        messages = []
        
        for line in content.strip().split("\n"):
            if line:
                data = json.loads(line)
                messages.append(ChatMessage.from_dict(data))
        
        # Apply limit if specified (return most recent)
        if limit and len(messages) > limit:
            messages = messages[-limit:]
        
        logger.info(f"Retrieved {len(messages)} messages")
        return messages
        
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}", exc_info=True)
        raise


def get_user_sessions(user_id: str) -> List[ConversationSession]:
    """
    Get all conversation sessions for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        List of ConversationSession objects, sorted by updated_at (newest first)
    """
    logger.info(f"Retrieving sessions for user={user_id}")
    
    try:
        client = _get_storage_client()
        bucket = client.bucket(CHAT_HISTORY_BUCKET)
        
        # List all JSONL files in user's directory
        prefix = f"{CHAT_HISTORY_PATH}/{user_id}/"
        blobs = bucket.list_blobs(prefix=prefix)
        
        sessions = []
        for blob in blobs:
            # Extract session_id from path
            if blob.name.endswith(".jsonl"):
                session_id = blob.name.split("/")[-1].replace(".jsonl", "")
                
                # Try to load session metadata
                session = _load_session_metadata(user_id, session_id)
                if session:
                    sessions.append(session)
        
        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        
        logger.info(f"Found {len(sessions)} sessions for user={user_id}")
        return sessions
        
    except Exception as e:
        logger.error(f"Error retrieving user sessions: {e}", exc_info=True)
        raise


def _load_session_metadata(user_id: str, session_id: str) -> Optional[ConversationSession]:
    """
    Load session metadata from GCS.
    Metadata is stored in: gs://{bucket}/chat_history/{user_id}/.metadata/{session_id}.json
    
    If metadata doesn't exist, generate it from conversation history.
    
    Args:
        user_id: User ID
        session_id: Session ID
    
    Returns:
        ConversationSession or None if session doesn't exist
    """
    try:
        client = _get_storage_client()
        bucket = client.bucket(CHAT_HISTORY_BUCKET)
        
        metadata_path = f"{CHAT_HISTORY_PATH}/{user_id}/.metadata/{session_id}.json"
        metadata_blob = bucket.blob(metadata_path)
        
        if metadata_blob.exists():
            data = json.loads(metadata_blob.download_as_text())
            return ConversationSession.from_dict(data)
        
        # Generate metadata from conversation history
        messages = get_conversation_history(user_id, session_id)
        if not messages:
            return None
        
        # Create session metadata
        first_message = messages[0]
        title = first_message.content[:50] + "..." if len(first_message.content) > 50 else first_message.content
        
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            title=title,
            created_at=first_message.timestamp,
            updated_at=messages[-1].timestamp,
            message_count=len(messages)
        )
        
        # Save metadata
        metadata_blob.upload_from_string(
            json.dumps(session.to_dict(), indent=2),
            content_type="application/json"
        )
        
        return session
        
    except Exception as e:
        logger.error(f"Error loading session metadata: {e}", exc_info=True)
        return None


def get_session_metadata(user_id: str, session_id: str) -> Optional[ConversationSession]:
    """
    Public helper to fetch session metadata even if no messages exist yet.
    """
    return _load_session_metadata(user_id, session_id)


def _update_session_metadata(user_id: str, session_id: str, tokens_to_add: int = 0) -> None:
    """
    Update session metadata after adding a message.
    
    Args:
        user_id: User ID
        session_id: Session ID
        tokens_to_add: Number of tokens to add to session total
    """
    try:
        session = _load_session_metadata(user_id, session_id)
        if not session:
            return
        
        # Update timestamp, message count, and tokens
        session.updated_at = datetime.utcnow().isoformat()
        messages = get_conversation_history(user_id, session_id)
        session.message_count = len(messages)
        session.total_tokens += tokens_to_add
        
        # Save updated metadata
        client = _get_storage_client()
        bucket = client.bucket(CHAT_HISTORY_BUCKET)
        metadata_path = f"{CHAT_HISTORY_PATH}/{user_id}/.metadata/{session_id}.json"
        metadata_blob = bucket.blob(metadata_path)
        
        metadata_blob.upload_from_string(
            json.dumps(session.to_dict(), indent=2),
            content_type="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error updating session metadata: {e}", exc_info=True)


def create_new_session(user_id: str, title: Optional[str] = None) -> ConversationSession:
    """
    Create a new conversation session for a user.
    
    Args:
        user_id: User ID
        title: Optional session title
    
    Returns:
        New ConversationSession
    """
    session_id = str(uuid.uuid4())
    
    session = ConversationSession(
        session_id=session_id,
        user_id=user_id,
        title=title or "New Conversation",
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
        message_count=0
    )
    
    # Save metadata
    try:
        client = _get_storage_client()
        bucket = client.bucket(CHAT_HISTORY_BUCKET)
        metadata_path = f"{CHAT_HISTORY_PATH}/{user_id}/.metadata/{session_id}.json"
        metadata_blob = bucket.blob(metadata_path)
        
        metadata_blob.upload_from_string(
            json.dumps(session.to_dict(), indent=2),
            content_type="application/json"
        )
        
        logger.info(f"Created new session {session_id} for user={user_id}")
        
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise
    
    return session


def delete_session(user_id: str, session_id: str) -> bool:
    """
    Delete a conversation session and all its messages.
    
    Args:
        user_id: User ID
        session_id: Session ID
    
    Returns:
        True if deleted successfully
    """
    logger.info(f"Deleting session {session_id} for user={user_id}")
    
    try:
        client = _get_storage_client()
        bucket = client.bucket(CHAT_HISTORY_BUCKET)
        
        # Delete conversation history
        conversation_path = f"{CHAT_HISTORY_PATH}/{user_id}/{session_id}.jsonl"
        conversation_blob = bucket.blob(conversation_path)
        if conversation_blob.exists():
            conversation_blob.delete()
        
        # Delete metadata
        metadata_path = f"{CHAT_HISTORY_PATH}/{user_id}/.metadata/{session_id}.json"
        metadata_blob = bucket.blob(metadata_path)
        if metadata_blob.exists():
            metadata_blob.delete()
        
        logger.info(f"Deleted session {session_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        return False


def update_session_title(user_id: str, session_id: str, title: str) -> Optional[ConversationSession]:
    """
    Update the title of a conversation session.
    
    Args:
        user_id: User ID
        session_id: Session ID
        title: New title
    
    Returns:
        Updated ConversationSession or None if not found
    """
    logger.info(f"Updating title for session {session_id}")
    
    try:
        session = _load_session_metadata(user_id, session_id)
        if not session:
            return None
        
        session.title = title
        session.updated_at = datetime.utcnow().isoformat()
        
        # Save updated metadata
        client = _get_storage_client()
        bucket = client.bucket(CHAT_HISTORY_BUCKET)
        metadata_path = f"{CHAT_HISTORY_PATH}/{user_id}/.metadata/{session_id}.json"
        metadata_blob = bucket.blob(metadata_path)
        
        metadata_blob.upload_from_string(
            json.dumps(session.to_dict(), indent=2),
            content_type="application/json"
        )
        
        logger.info(f"Updated session title to: {title}")
        return session
        
    except Exception as e:
        logger.error(f"Error updating session title: {e}", exc_info=True)
        raise
