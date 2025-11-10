# Chat History Implementation - Quick Start

## What Was Built

Complete chat history and user authentication system for the CENTEF RAG platform with:

✅ **User Authentication**
- JWT bearer tokens (secure, time-limited)
- API keys (simple, long-lived)
- Multi-user isolation

✅ **Conversation Management**
- Session-based chat history
- Persistent storage in GCS
- Automatic message logging

✅ **API Endpoints**
- `POST /chat` - Send queries with auto-save
- `GET /chat/sessions` - List user conversations
- `GET /chat/history/{session_id}` - Retrieve messages
- Session CRUD operations

## Quick Setup

### 1. Install New Dependencies

```powershell
pip install python-jose[cryptography]
```

### 2. Update .env File

Add these lines to your `.env`:

```bash
# Chat History
CHAT_HISTORY_BUCKET=centef-rag-bucket
CHAT_HISTORY_PATH=chat_history

# Authentication
JWT_SECRET_KEY=change-this-to-a-long-random-string
ACCESS_TOKEN_EXPIRE_MINUTES=60
API_KEY_HEADER=X-API-Key
VALID_API_KEYS=test-api-key-123
```

**Generate a secure JWT secret:**
```powershell
# Using OpenSSL (if installed)
openssl rand -hex 32

# Or using Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Generate Test Credentials

```powershell
# Generate JWT token
python generate_test_token.py john_doe john@example.com

# Generate API key
python generate_test_token.py --api-key john_doe
```

### 4. Test the System

```powershell
# Test chat history storage
python test_chat_history.py

# Start the API server
cd apps/agent_api
python main.py
```

## Usage Examples

### Python Client Example

```python
import requests

# Generate authentication token
from shared.auth import generate_test_token
token = generate_test_token("john_doe", "john@example.com")

headers = {"Authorization": f"Bearer {token}"}

# Start a chat (creates new session automatically)
response = requests.post(
    "http://localhost:8080/chat",
    headers=headers,
    json={"query": "What is counter-terrorism financing?"}
)
result = response.json()
print(f"Session ID: {result['session_id']}")
print(f"Answer: {result['answer']}")

# Continue the conversation (use same session_id)
response2 = requests.post(
    "http://localhost:8080/chat",
    headers=headers,
    json={
        "query": "Can you give me examples?",
        "session_id": result['session_id']
    }
)

# Get conversation history
history = requests.get(
    f"http://localhost:8080/chat/history/{result['session_id']}",
    headers=headers
)
print(f"Conversation has {len(history.json())} messages")

# List all sessions
sessions = requests.get(
    "http://localhost:8080/chat/sessions",
    headers=headers
)
for session in sessions.json():
    print(f"- {session['title']} ({session['message_count']} messages)")
```

### curl Example

```powershell
# Get a token
$TOKEN = (python generate_test_token.py john_doe | Select-String "Token:" | ForEach-Object { $_.ToString().Split(" ")[1] })

# Start a chat
$RESPONSE = curl -X POST http://localhost:8080/chat `
  -H "Authorization: Bearer $TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"query": "What is AML?"}' | ConvertFrom-Json

# Get sessions
curl http://localhost:8080/chat/sessions `
  -H "Authorization: Bearer $TOKEN"

# Get history
curl "http://localhost:8080/chat/history/$($RESPONSE.session_id)" `
  -H "Authorization: Bearer $TOKEN"
```

## New Files Created

1. **`shared/chat_history.py`** - Chat history management
   - `ChatMessage` and `ConversationSession` schemas
   - CRUD operations for conversations
   - GCS storage with JSONL format

2. **`shared/auth.py`** - Authentication utilities
   - JWT token generation and verification
   - API key validation
   - User dependency injection for FastAPI

3. **`apps/agent_api/main.py`** - Updated with chat endpoints
   - `POST /chat` - Authenticated queries
   - `GET /chat/sessions` - List conversations
   - `GET /chat/history/{session_id}` - Get messages
   - Session management endpoints

4. **`test_chat_history.py`** - Comprehensive test suite
   - Multi-user isolation tests
   - Message ordering and retrieval
   - Session metadata validation

5. **`generate_test_token.py`** - Token generation utility
   - Generate JWT tokens for testing
   - Generate API keys

6. **`CHAT_HISTORY.md`** - Complete documentation
   - API reference
   - Usage examples
   - Security considerations
   - Troubleshooting guide

## Key Features

### 🔐 Authentication
- **JWT Tokens**: Secure, short-lived (60 min default)
- **API Keys**: Simple, long-lived alternative
- Both methods fully supported

### 💬 Chat Sessions
- **Auto-create**: First query creates new session
- **Persistent**: All messages saved to GCS
- **Organized**: Sessions have titles, timestamps, message counts

### 👥 Multi-User Support
- **Isolated**: Each user sees only their data
- **Secure**: Authentication required for all chat endpoints
- **Scalable**: User data stored in separate GCS paths

### 📝 Message Metadata
Every assistant response includes:
- Full answer text
- Source documents used
- Explicit citations (≥5 required)
- Gemini model used
- Query parameters (temperature, max_results)

## Testing Checklist

- [ ] Install `python-jose[cryptography]`
- [ ] Update `.env` with chat configuration
- [ ] Generate JWT secret key
- [ ] Run `python test_chat_history.py` (should pass all tests)
- [ ] Generate test token with `generate_test_token.py`
- [ ] Start API server: `python apps/agent_api/main.py`
- [ ] Test `/chat` endpoint with authentication
- [ ] Verify conversation history persists
- [ ] Test multi-user isolation with different tokens

## Integration with Existing Code

The chat functionality integrates seamlessly:

1. **Query Flow**: `POST /chat` → `search_two_tier()` → `synthesize_answer()` → Save to history
2. **Storage**: Uses same GCS bucket as manifest (`CHAT_HISTORY_BUCKET`)
3. **No Breaking Changes**: Existing `/search` endpoint still works (no auth required)
4. **Gradual Migration**: Add authentication to other endpoints as needed

## Next Steps

1. **Production Deployment**:
   - Generate strong JWT secret key
   - Configure HTTPS/TLS
   - Set up proper API key management
   - Add rate limiting

2. **Frontend Integration**:
   - Implement login/authentication
   - Build chat UI with session list
   - Show conversation history
   - Allow session management (rename, delete)

3. **Enhancements**:
   - Add conversation search
   - Export chat history
   - Share conversations
   - Real-time updates (WebSocket)
   - Conversation summarization

## Troubleshooting

**Import errors (jose, FastAPI, etc.)**
```powershell
pip install -r requirements.txt
```

**Authentication fails**
- Check `.env` has `JWT_SECRET_KEY` and `VALID_API_KEYS`
- Verify token hasn't expired (default: 60 minutes)
- Ensure `Authorization: Bearer <token>` header is set

**Chat history not saving**
- Verify `CHAT_HISTORY_BUCKET` points to valid GCS bucket
- Check GCS permissions
- Look for errors in console output

**Session not found**
- Ensure session belongs to authenticated user
- Check session wasn't deleted

## Documentation

📖 **Complete Documentation**: See `CHAT_HISTORY.md` for:
- Full API reference
- More usage examples
- Security best practices
- Production deployment guide

## Support

For questions or issues:
1. Check `CHAT_HISTORY.md` documentation
2. Run test suite: `python test_chat_history.py`
3. Review API server logs for errors
4. Check `.env` configuration
