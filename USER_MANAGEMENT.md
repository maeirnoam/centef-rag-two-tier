# User Management Guide

## Overview

The CENTEF RAG system supports three user management approaches:

1. **Simple Mode** (Current) - Manual token/API key generation
2. **Database Mode** (Implemented) - User registration with passwords
3. **OAuth2/SSO** (Future) - Integration with Google, GitHub, etc.

## Current Approach: Simple Mode

### How It Works
- No user database required
- Users identified by JWT token or API key
- User ID comes from authentication credentials

### Managing Users

#### Add User via JWT Token
```powershell
# Generate token for a user
python generate_test_token.py john_doe john@example.com
python generate_test_token.py alice alice@example.com

# Users are created implicitly when they use the token
# Their chat history is stored under their user_id
```

#### Add User via API Key
```powershell
# Generate API key
python generate_test_token.py --api-key john_doe

# Add to .env file:
VALID_API_KEYS=john_abc123,alice_xyz789,bob_def456
```

### Limitations
- ❌ No password authentication
- ❌ No user registration flow
- ❌ Manual token generation
- ❌ Tokens expire (default: 60 minutes)

---

## Database Mode: User Registration

A complete user management system is now available in `shared/user_management.py`.

### Storage
Users stored in GCS: `gs://{USER_DATA_BUCKET}/users/users.jsonl`

### User Schema
```json
{
  "user_id": "john_doe",
  "email": "john@example.com",
  "hashed_password": "salt$hash",
  "full_name": "John Doe",
  "created_at": "2025-11-09T10:00:00Z",
  "last_login": "2025-11-09T11:30:00Z",
  "roles": ["user"],
  "is_active": true
}
```

### Setup

**1. Configure environment:**
```bash
# Add to .env
USER_DATA_BUCKET=centef-rag-bucket
USER_DATA_PATH=users/users.jsonl
```

**2. Import dependencies in your code:**
```python
from shared.user_management import create_user, authenticate_user
```

### Managing Users

#### Create User (CLI)
```powershell
python shared/user_management.py create john@example.com password123 "John Doe"
python shared/user_management.py create alice@acme.com secret456 "Alice Smith"
```

#### List All Users
```powershell
python shared/user_management.py list
```

Output:
```
Total users: 2

  john@example.com (john) - John Doe [✅ Active]
    Roles: user
    Created: 2025-11-09T10:00:00Z
    Last login: 2025-11-09T11:30:00Z

  alice@acme.com (alice) - Alice Smith [✅ Active]
    Roles: user
    Created: 2025-11-09T10:05:00Z
```

#### Deactivate User
```powershell
python shared/user_management.py deactivate john@example.com
```

### API Endpoints

The following endpoints are now available:

#### `POST /auth/register`
Register a new user and receive JWT token.

**Request:**
```json
{
  "email": "john@example.com",
  "password": "secure-password-123",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user_id": "john",
  "email": "john@example.com"
}
```

#### `POST /auth/login`
Login with email and password.

**Request:**
```json
{
  "email": "john@example.com",
  "password": "secure-password-123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user_id": "john",
  "email": "john@example.com"
}
```

#### `GET /auth/me`
Get current user information (requires authentication).

**Response:**
```json
{
  "user_id": "john",
  "email": "john@example.com",
  "full_name": "John Doe",
  "roles": ["user"],
  "created_at": "2025-11-09T10:00:00Z",
  "last_login": "2025-11-09T11:30:00Z"
}
```

### Usage Example

```python
import requests

# Register a new user
register_response = requests.post(
    "http://localhost:8000/auth/register",
    json={
        "email": "john@example.com",
        "password": "secure-password",
        "full_name": "John Doe"
    }
)

token = register_response.json()["access_token"]
print(f"Registered! Token: {token}")

# Or login with existing user
login_response = requests.post(
    "http://localhost:8000/auth/login",
    json={
        "email": "john@example.com",
        "password": "secure-password"
    }
)

token = login_response.json()["access_token"]

# Use token for authenticated requests
headers = {"Authorization": f"Bearer {token}"}

# Get user info
me = requests.get("http://localhost:8000/auth/me", headers=headers)
print(me.json())

# Start chatting
chat = requests.post(
    "http://localhost:8000/chat",
    headers=headers,
    json={"query": "What is CTF?"}
)
print(chat.json()["answer"])
```

---

## Production Considerations

### Security Improvements Needed

**1. Use bcrypt for password hashing:**
```powershell
pip install bcrypt
```

Update `shared/user_management.py`:
```python
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())
```

**2. Add password requirements:**
- Minimum length (8+ characters)
- Complexity rules (uppercase, lowercase, numbers, symbols)
- Password strength validation

**3. Implement token refresh:**
```python
@app.post("/auth/refresh")
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Generate a new token before the current one expires"""
    new_token = create_access_token({
        "sub": current_user.user_id,
        "email": current_user.email
    })
    return {"access_token": new_token, "token_type": "bearer"}
```

**4. Add rate limiting:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")  # Max 5 login attempts per minute
async def login(request: LoginRequest):
    ...
```

**5. Add email verification:**
- Send verification email on registration
- Store verification token
- Verify before allowing login

**6. Implement password reset:**
- Send password reset email with token
- Verify token and allow password change

### Role-Based Access Control (RBAC)

Add role checking:

```python
from functools import wraps

def require_role(required_role: str):
    """Decorator to require specific role"""
    async def role_checker(current_user: User = Depends(get_current_user)):
        if required_role not in current_user.roles:
            raise HTTPException(403, "Insufficient permissions")
        return current_user
    return role_checker

# Usage
@app.delete("/admin/users/{user_id}")
async def delete_user_admin(
    user_id: str,
    current_user: User = Depends(require_role("admin"))
):
    """Only admins can delete users"""
    ...
```

---

## Migration from Simple to Database Mode

**Step 1:** Create users for existing API key/token users
```powershell
# For each existing user
python shared/user_management.py create john@example.com temp-password "John Doe"
```

**Step 2:** Have users login to get new tokens
```
POST /auth/login with their credentials
```

**Step 3:** Migrate chat history (optional)
```python
# Chat history is already keyed by user_id
# If user_id format changed, you may need to migrate:
from shared.chat_history import get_user_sessions
from google.cloud import storage

# Example: Move from "apikey_abc123" to "john"
old_user_id = "apikey_abc123"
new_user_id = "john"

# Copy chat history in GCS
# gs://bucket/chat_history/old_user_id/* -> gs://bucket/chat_history/new_user_id/*
```

---

## Future: OAuth2 Integration

For enterprise deployments, consider OAuth2:

### Google OAuth2
```python
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()
oauth.register(
    name='google',
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@app.get('/auth/login/google')
async def login_google(request: Request):
    redirect_uri = request.url_for('auth_google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get('/auth/callback/google')
async def auth_google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = await oauth.google.parse_id_token(request, token)
    
    # Create or get user
    # Generate JWT token
    # Return to frontend
```

### Firebase Authentication
```python
from firebase_admin import auth

@app.post("/auth/firebase")
async def auth_firebase(id_token: str):
    """Verify Firebase ID token"""
    decoded_token = auth.verify_id_token(id_token)
    user_id = decoded_token['uid']
    email = decoded_token.get('email')
    
    # Create user if doesn't exist
    # Generate JWT token
    # Return access token
```

---

## Summary

**Current State:**
- ✅ Simple JWT/API key authentication
- ✅ User registration with passwords
- ✅ Login endpoint
- ✅ User profile storage in GCS

**Recommended for Production:**
- [ ] Switch to bcrypt for password hashing
- [ ] Add email verification
- [ ] Implement password reset
- [ ] Add rate limiting on auth endpoints
- [ ] Use proper secrets management (Google Secret Manager)
- [ ] Consider OAuth2 for enterprise SSO
- [ ] Implement RBAC for different permission levels
- [ ] Add audit logging for user actions

**To Get Started:**
```powershell
# Create your first user
python shared/user_management.py create admin@example.com AdminPass123 "Admin User"

# Test registration endpoint
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test123!", "full_name": "Test User"}'
```

Users can now register themselves via the API, or you can create them via CLI!
