# Chat History & User Authentication

This document describes the chat history and authentication features of the CENTEF RAG system.

## Overview

The CENTEF RAG system now supports **authenticated users** with **persistent chat history**. Each user has:
- Individual conversation sessions
- Complete message history with citations and sources
- Session management (create, list, delete, rename)
- Automatic conversation tracking

## Architecture

### Data Storage
- **Location**: Google Cloud Storage (same bucket as manifest)
- **Path**: `gs://{CHAT_HISTORY_BUCKET}/chat_history/{user_id}/{session_id}.jsonl`
- **Format**: JSONL (one message per line)
- **Metadata**: `gs://{CHAT_HISTORY_BUCKET}/chat_history/{user_id}/.metadata/{session_id}.json`

### Authentication Methods

1. **JWT Bearer Tokens** (Recommended)
   - Secure, time-limited tokens
   - Include user metadata (email, roles)
   - Default expiration: 60 minutes

2. **API Keys** (Simple alternative)
   - Long-lived static keys
   - Good for service-to-service communication
   - Configure via environment variables

## Setup

### 1. Install Dependencies

```powershell
pip install python-jose[cryptography]
```

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Chat History Configuration
CHAT_HISTORY_BUCKET=centef-rag-bucket
CHAT_HISTORY_PATH=chat_history

# Authentication Configuration
JWT_SECRET_KEY=your-secret-key-change-in-production-use-long-random-string
ACCESS_TOKEN_EXPIRE_MINUTES=60
API_KEY_HEADER=X-API-Key
VALID_API_KEYS=your-api-key-1,your-api-key-2
```

### 3. Generate Test Credentials

```powershell
# Generate JWT token
python generate_test_token.py john_doe john@example.com

# Generate API key
python generate_test_token.py --api-key john_doe
```

## API Endpoints

### Chat Endpoints

#### `POST /chat`
Send a chat message and get an AI response.

**Request:**
```json
{
  "query": "What is counter-terrorism financing?",
  "session_id": "optional-session-id",  // If null, creates new session
  "max_chunks": 8,
  "max_summaries": 3,
  "temperature": 0.2
}
```

**Response:**
```json
{
  "message_id": "uuid",
  "session_id": "uuid",
  "answer": "CTF refers to...",
  "sources": [...],
  "explicit_citations": [...],
  "model_used": "gemini-2.0-flash-exp"
}
```

#### `GET /chat/sessions`
Get all conversation sessions for the current user.

**Response:**
```json
[
  {
    "session_id": "uuid",
    "user_id": "john_doe",
    "title": "Discussion about CTF",
    "created_at": "2025-11-09T10:00:00Z",
    "updated_at": "2025-11-09T10:15:00Z",
    "message_count": 6
  }
]
```

#### `GET /chat/history/{session_id}`
Get conversation history for a specific session.

**Query Parameters:**
- `limit` (optional): Maximum number of messages to return (most recent)

**Response:**
```json
[
  {
    "message_id": "uuid",
    "session_id": "uuid",
    "role": "user",
    "content": "What is CTF?",
    "timestamp": "2025-11-09T10:00:00Z",
    "sources": [],
    "citations": []
  },
  {
    "message_id": "uuid",
    "session_id": "uuid",
    "role": "assistant",
    "content": "CTF refers to...",
    "timestamp": "2025-11-09T10:00:05Z",
    "sources": [...],
    "citations": [...],
    "model_used": "gemini-2.0-flash-exp"
  }
]
```

#### `POST /chat/sessions`
Create a new conversation session.

**Query Parameters:**
- `title` (optional): Session title (default: "New Conversation")

**Response:**
```json
{
  "session_id": "uuid",
  "user_id": "john_doe",
  "title": "New Conversation",
  "created_at": "2025-11-09T10:00:00Z",
  "updated_at": "2025-11-09T10:00:00Z",
  "message_count": 0
}
```

#### `PATCH /chat/sessions/{session_id}/title`
Update the title of a session.

**Query Parameters:**
- `title`: New title

**Response:**
```json
{
  "session_id": "uuid",
  "user_id": "john_doe",
  "title": "Updated Title",
  "created_at": "2025-11-09T10:00:00Z",
  "updated_at": "2025-11-09T10:30:00Z",
  "message_count": 6
}
```

#### `DELETE /chat/sessions/{session_id}`
Delete a session and all its messages.

**Response:**
```json
{
  "message": "Session deleted successfully",
  "session_id": "uuid"
}
```

## Usage Examples

### Using JWT Tokens

```python
import requests

# Generate token (for testing)
from shared.auth import generate_test_token
token = generate_test_token("john_doe", "john@example.com")

# Make authenticated requests
headers = {"Authorization": f"Bearer {token}"}

# Start a new chat
response = requests.post(
    "http://localhost:8000/chat",
    headers=headers,
    json={"query": "What is AML?"}
)
print(response.json())

# Get conversation history
session_id = response.json()["session_id"]
history = requests.get(
    f"http://localhost:8000/chat/history/{session_id}",
    headers=headers
)
print(history.json())

# List all sessions
sessions = requests.get(
    "http://localhost:8000/chat/sessions",
    headers=headers
)
print(sessions.json())
```

### Using API Keys

```python
import requests

api_key = "your-api-key"
headers = {"X-API-Key": api_key}

# Make authenticated requests
response = requests.post(
    "http://localhost:8000/chat",
    headers=headers,
    json={"query": "What is CTF?"}
)
print(response.json())
```

### Using curl

```bash
# Generate token
$TOKEN = python generate_test_token.py john_doe

# Start a chat
curl -X POST http://localhost:8000/chat `
  -H "Authorization: Bearer $TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"query": "What is counter-terrorism financing?"}'

# Get sessions
curl http://localhost:8000/chat/sessions `
  -H "Authorization: Bearer $TOKEN"

# Get history
curl "http://localhost:8000/chat/history/{session_id}" `
  -H "Authorization: Bearer $TOKEN"
```

## Testing

### Unit Tests

```powershell
# Test chat history storage and retrieval
python test_chat_history.py
```

This tests:
- Creating sessions for multiple users
- Multi-user isolation
- Message ordering and retrieval
- Session metadata management
- Citation and source storage

### Integration Tests

Start the API server:
```powershell
cd apps/agent_api
python main.py
```

In another terminal:
```powershell
# Generate token
python generate_test_token.py test_user

# Test endpoints with the generated token
```

## Data Schema

### ChatMessage
```python
{
    "message_id": str,        # Unique message ID
    "session_id": str,        # Session ID
    "user_id": str,           # User ID
    "role": str,              # "user" | "assistant" | "system"
    "content": str,           # Message content
    "timestamp": str,         # ISO 8601 timestamp
    "sources": List[Dict],    # Source documents (for assistant messages)
    "citations": List[str],   # Explicit citations (for assistant messages)
    "model_used": str,        # Gemini model used (for assistant messages)
    "query_metadata": Dict    # Additional query parameters
}
```

### ConversationSession
```python
{
    "session_id": str,        # Unique session ID
    "user_id": str,           # User ID
    "title": str,             # Session title
    "created_at": str,        # ISO 8601 timestamp
    "updated_at": str,        # ISO 8601 timestamp
    "message_count": int      # Number of messages in session
}
```

## Security Considerations

### Production Setup

1. **JWT Secret Key**
   - Generate a strong random key: `openssl rand -hex 32`
   - Store securely (environment variable or secret manager)
   - Never commit to version control

2. **API Keys**
   - Generate cryptographically secure keys
   - Store in environment variables
   - Rotate regularly
   - Use different keys per user/service

3. **Token Expiration**
   - JWT tokens expire after configured time (default: 60 minutes)
   - Implement token refresh mechanism for production
   - API keys don't expire but can be revoked

4. **HTTPS**
   - Always use HTTPS in production
   - Never send tokens over unencrypted connections

5. **Rate Limiting**
   - Implement rate limiting per user
   - Prevent abuse of chat endpoints

## Multi-User Isolation

The system ensures complete isolation between users:
- Each user can only access their own sessions
- Chat history is stored in user-specific directories
- Authentication is required for all chat endpoints
- User ID is extracted from JWT token or API key

## Troubleshooting

### "Could not validate credentials"
- Check that JWT token is valid and not expired
- Verify API key is in `VALID_API_KEYS` environment variable
- Ensure `Authorization` header or `X-API-Key` header is set

### "Session not found"
- Verify session_id belongs to the authenticated user
- Check that session hasn't been deleted

### Chat history not persisting
- Verify `CHAT_HISTORY_BUCKET` environment variable is set
- Check GCS permissions for the bucket
- Look for errors in application logs

### Import errors for jose or FastAPI
- Install missing dependencies: `pip install -r requirements.txt`
- Ensure `python-jose[cryptography]` is installed

## Future Enhancements

Potential improvements:
- OAuth2 integration (Google, GitHub, etc.)
- User roles and permissions (admin, user, readonly)
- Conversation sharing and collaboration
- Export conversation history
- Search within conversation history
- Conversation summarization
- Token refresh mechanism
- WebSocket support for real-time updates
