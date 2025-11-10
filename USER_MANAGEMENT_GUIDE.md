# User Management Testing Guide

## Overview
The user management page allows admins to create, edit, and delete users. It's accessible only to users with the "admin" role.

## Prerequisites
1. Backend running on port 8080: `cd apps/agent_api && python main.py`
2. Frontend running on port 3000: `cd apps/frontend && python serve.py`
3. Logged in as admin (admin@centef.org / Admin123!)

## Features

### 1. View All Users
- Lists all users in a table showing:
  - Email
  - Full Name
  - Roles (badge display)
  - Status (Active/Inactive)
  - Total Tokens used
  - Created date
  - Last Login date
  - Actions (Edit, Reset Password, Delete)

### 2. Create New User
- Click "+ Create User" button
- Fill in the form:
  - Email (required, must be unique)
  - Full Name (required)
  - Password (required, min 8 characters)
  - Admin Access checkbox (grants both 'user' and 'admin' roles)
- Click "Create User"

**Role Assignment:**
- Without admin checkbox: `["user"]`
- With admin checkbox: `["user", "admin"]`

### 3. Edit User
- Click "Edit" button for any user
- Can change:
  - Full Name
  - Admin Access (toggle admin role)
  - Active status (inactive users cannot log in)
- Email cannot be changed
- Click "Save Changes"

### 4. Reset Password
- Click "Reset Password" button
- Enter new password (min 8 characters)
- Confirm password
- Click "Reset Password"

### 5. Delete User (Deactivate)
- Click "Delete" button (red)
- Confirmation prompt requires typing "DELETE"
- Soft delete: sets `is_active = False`
- User cannot log in after deletion
- **Protection**: Cannot delete your own account

## API Endpoints

### GET /admin/users
List all users (admin only)
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/admin/users
```

### POST /admin/users
Create a new user (admin only)
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"new@example.com","password":"Pass123!","full_name":"New User","roles":["user"]}' \
  http://localhost:8080/admin/users
```

### PUT /admin/users/{user_id}
Update a user (admin only)
```bash
curl -X PUT -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Updated Name","roles":["user","admin"],"is_active":true}' \
  http://localhost:8080/admin/users/user_id
```

### DELETE /admin/users/{user_id}
Delete (deactivate) a user (admin only)
```bash
curl -X DELETE -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/admin/users/user_id
```

## Testing

### Automated Test
Run the test script to verify all endpoints:
```powershell
python test_user_management.py
```

This tests:
- ✅ List all users
- ✅ Create new user
- ✅ Update user
- ✅ Reset password
- ✅ Delete user

### Manual Test via Frontend
1. Open browser: http://localhost:3000/login.html
2. Login as admin@centef.org
3. Click "Users" in navigation (admin-only link)
4. Try each operation:
   - Create a test user
   - Edit the user's name and roles
   - Reset the user's password
   - Delete the user
   - Verify user appears as "Inactive" after deletion

## Security Features

1. **Admin-only access**: All endpoints require admin role
2. **JWT authentication**: Token required in Authorization header
3. **Self-deletion prevention**: Cannot delete your own account
4. **Password hashing**: Passwords stored as SHA-256 + salt
5. **Soft delete**: Users deactivated, not permanently deleted
6. **Confirmation prompts**: Must type "DELETE" to confirm deletion

## Data Storage

Users stored in GCS:
- Bucket: `centef-rag-bucket` (from `USER_DATA_BUCKET` env var)
- Path: `users/users.jsonl` (from `USER_DATA_PATH` env var)
- Format: JSONL (one JSON object per line)

## Roles

- `["user"]` - Can use chat, view own sessions
- `["admin"]` - Can access Manifest, Users, and admin endpoints
- `["user", "admin"]` - Both permissions (most admins have both)

## Common Issues

### "User not found" error
- Check the user_id is correct
- Refresh the page to reload data

### Cannot see Users link
- Ensure you're logged in as admin
- Check that admin role is in JWT token

### Password reset fails
- Ensure new password is min 8 characters
- Check passwords match

### Cannot delete user
- Cannot delete yourself
- Must type "DELETE" exactly

## Next Steps

Future enhancements could include:
- Bulk user operations
- User activity logs
- Role management (custom roles)
- Email verification
- Password reset via email
- Two-factor authentication
- User impersonation (for support)
