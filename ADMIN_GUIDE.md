# Admin User Guide

## Overview

The CENTEF RAG system now supports **role-based access control (RBAC)** with two primary roles:

- **Admin**: Full system access, document approval, user management
- **User**: Chat access, view documents, manage own sessions

## Sample Users

Run the initialization script to create sample users:

```powershell
python init_users.py
```

This creates:

| Email | Password | Role | Capabilities |
|-------|----------|------|--------------|
| admin@centef.org | Admin123! | Admin | Full access, approvals, user management |
| user@centef.org | User123! | User | Chat, view documents |

⚠️ **Change these passwords immediately in production!**

## Admin Capabilities

### 1. Document Approval Workflow

Admins can review and approve document metadata before indexing.

#### View Pending Approvals
```bash
GET /admin/manifest/pending
Authorization: Bearer <admin-token>
```

Response:
```json
[
  {
    "source_id": "doc-123",
    "filename": "terrorism-financing-report.pdf",
    "title": "Terrorism Financing Report",
    "status": "pending_approval",
    "approved": false,
    "author": "John Smith",
    "organization": "FATF",
    "date": "2025-01-15",
    "tags": ["ctf", "aml", "fatf"]
  }
]
```

#### Approve a Document
```bash
PUT /admin/manifest/{source_id}/approve
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "approved": true,
  "notes": "Metadata verified and approved"
}
```

When a document is approved:
- `approved` is set to `true`
- `status` automatically changes from `pending_approval` to `pending_embedding`
- Document is queued for indexing

#### Reject a Document
```bash
PUT /admin/manifest/{source_id}/approve
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "approved": false,
  "notes": "Incorrect metadata, needs revision"
}
```

### 2. System Dashboard

View system statistics:

```bash
GET /admin/stats
Authorization: Bearer <admin-token>
```

Response:
```json
{
  "documents": {
    "total": 150,
    "by_status": {
      "pending_processing": 5,
      "pending_summary": 3,
      "pending_approval": 8,
      "pending_embedding": 2,
      "embedded": 132
    },
    "pending_approval": 8
  },
  "users": {
    "total": 25,
    "active": 23,
    "admins": 3
  }
}
```

### 3. User Management

#### List All Users
```bash
GET /admin/users
Authorization: Bearer <admin-token>
```

Response:
```json
[
  {
    "user_id": "admin",
    "email": "admin@centef.org",
    "full_name": "CENTEF Administrator",
    "roles": ["admin", "user"],
    "is_active": true,
    "created_at": "2025-11-09T10:00:00Z",
    "last_login": "2025-11-09T15:30:00Z"
  },
  {
    "user_id": "john",
    "email": "john@researcher.org",
    "full_name": "John Doe",
    "roles": ["user"],
    "is_active": true,
    "created_at": "2025-11-08T14:20:00Z",
    "last_login": "2025-11-09T09:15:00Z"
  }
]
```

#### Create Admin User (CLI)
```powershell
python shared/user_management.py create admin2@centef.org SecurePass123 "Admin Name" admin
```

#### Deactivate User (CLI)
```powershell
python shared/user_management.py deactivate user@example.com
```

## Admin Workflow Examples

### Example 1: Document Review and Approval

```python
import requests

# Login as admin
login = requests.post(
    "http://localhost:8000/auth/login",
    json={
        "email": "admin@centef.org",
        "password": "Admin123!"
    }
)
admin_token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {admin_token}"}

# Get pending approvals
pending = requests.get(
    "http://localhost:8000/admin/manifest/pending",
    headers=headers
)

print(f"Documents pending approval: {len(pending.json())}")

# Review each document
for doc in pending.json():
    print(f"\nReviewing: {doc['title']}")
    print(f"  Author: {doc['author']}")
    print(f"  Organization: {doc['organization']}")
    print(f"  Tags: {', '.join(doc['tags'])}")
    
    # Approve the document
    approval = requests.put(
        f"http://localhost:8000/admin/manifest/{doc['source_id']}/approve",
        headers=headers,
        json={
            "approved": True,
            "notes": "Reviewed and approved"
        }
    )
    
    print(f"  ✅ Approved! Status: {approval.json()['status']}")
```

### Example 2: Monitor System Health

```python
import requests

# Login as admin
login = requests.post(
    "http://localhost:8000/auth/login",
    json={"email": "admin@centef.org", "password": "Admin123!"}
)
headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

# Get system stats
stats = requests.get(
    "http://localhost:8000/admin/stats",
    headers=headers
).json()

print("System Status:")
print(f"  Total Documents: {stats['documents']['total']}")
print(f"  Pending Approval: {stats['documents']['pending_approval']}")
print(f"  Active Users: {stats['users']['active']}")
print(f"  Admin Users: {stats['users']['admins']}")

# Alert if too many pending approvals
if stats['documents']['pending_approval'] > 10:
    print("\n⚠️  WARNING: High number of pending approvals!")
```

## Regular User Capabilities

Regular users can:
- ✅ Register: `POST /auth/register`
- ✅ Login: `POST /auth/login`
- ✅ Chat: `POST /chat`
- ✅ View their chat history: `GET /chat/history/{session_id}`
- ✅ Manage their sessions: `GET /chat/sessions`, `DELETE /chat/sessions/{id}`
- ✅ View manifest: `GET /manifest`
- ❌ Cannot approve documents
- ❌ Cannot view admin stats
- ❌ Cannot manage other users

## Permission Errors

When a regular user tries to access admin endpoints:

```json
{
  "detail": "Insufficient permissions. Required role: admin"
}
```

HTTP Status: `403 Forbidden`

## CLI Commands

### Create Users
```powershell
# Regular user
python shared/user_management.py create user@example.com Password123 "User Name"

# Admin user
python shared/user_management.py create admin@example.com Password123 "Admin Name" admin

# User with multiple roles
python shared/user_management.py create power@example.com Password123 "Power User" "user,admin"
```

### List All Users
```powershell
python shared/user_management.py list
```

Output:
```
Total users: 3

  admin@centef.org (admin) - CENTEF Administrator [✅ Active]
    Roles: admin, user
    Created: 2025-11-09T10:00:00Z
    Last login: 2025-11-09T15:30:00Z

  user@centef.org (user) - CENTEF User [✅ Active]
    Roles: user
    Created: 2025-11-09T10:05:00Z
```

### Deactivate User
```powershell
python shared/user_management.py deactivate user@example.com
```

## Security Best Practices

### 1. Secure JWT Secret
Generate a strong secret key:
```powershell
# Using OpenSSL
openssl rand -hex 32

# Or Python
python -c "import secrets; print(secrets.token_hex(32))"
```

Add to `.env`:
```bash
JWT_SECRET_KEY=<generated-key>
```

### 2. Change Default Passwords
Immediately after running `init_users.py`, change the default passwords:

```powershell
python shared/user_management.py deactivate admin@centef.org
python shared/user_management.py create admin@centef.org <strong-password> "Admin" admin

python shared/user_management.py deactivate user@centef.org
python shared/user_management.py create user@centef.org <strong-password> "User" user
```

### 3. Use HTTPS in Production
Never send credentials over unencrypted connections:
- Deploy behind HTTPS/TLS
- Use secure proxy (nginx, Caddy)
- Enable HSTS headers

### 4. Implement Rate Limiting
Protect against brute force attacks:
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")  # Max 5 attempts per minute
async def login(request: LoginRequest):
    ...
```

### 5. Audit Admin Actions
Log all admin operations:
```python
@app.put("/admin/manifest/{source_id}/approve")
async def approve_document(
    source_id: str,
    approval: ApprovalRequest,
    current_user: User = Depends(require_role("admin"))
):
    # Log admin action
    logger.info(f"ADMIN ACTION: {current_user.email} {'approved' if approval.approved else 'rejected'} document {source_id}")
    ...
```

## Troubleshooting

### Admin Can't Approve Documents
- Verify user has "admin" role: `GET /auth/me`
- Check token hasn't expired (default: 60 minutes)
- Ensure using correct endpoint: `/admin/manifest/{id}/approve`

### Regular Users Can Access Admin Endpoints
- Check `require_role("admin")` dependency is applied to endpoint
- Verify user roles are properly loaded from database
- Test with: `GET /admin/stats` (should return 403 for non-admins)

### Users Not Persisting
- Verify `USER_DATA_BUCKET` is set in `.env`
- Check GCS bucket permissions
- Look for errors in console: `python shared/user_management.py list`

## Complete Admin Workflow

```powershell
# 1. Initialize system
python init_users.py

# 2. Start API server
cd apps/agent_api
python main.py

# 3. Login as admin (in another terminal or use Postman)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@centef.org","password":"Admin123!"}'

# 4. Get pending approvals
curl http://localhost:8000/admin/manifest/pending \
  -H "Authorization: Bearer <token>"

# 5. Approve a document
curl -X PUT http://localhost:8000/admin/manifest/doc-123/approve \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"approved":true,"notes":"Approved"}'

# 6. Check system stats
curl http://localhost:8000/admin/stats \
  -H "Authorization: Bearer <token>"
```

Your admin system is now fully configured! 🎉
