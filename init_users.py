"""
Initialize CENTEF RAG system with sample users.

Creates:
- Admin user: admin@centef.org (password: Admin123!)
- Regular user: user@centef.org (password: User123!)

Run this once to set up the system for the first time.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.user_management import create_user, list_all_users

print("=" * 80)
print("CENTEF RAG - Initialize System with Sample Users")
print("=" * 80)
print()

# Check if users already exist
existing_users = list_all_users()
if existing_users:
    print(f"⚠️  Warning: {len(existing_users)} user(s) already exist:")
    for user in existing_users:
        print(f"   - {user.email} ({', '.join(user.roles)})")
    print()
    
    response = input("Do you want to add sample users anyway? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        sys.exit(0)
    print()

# Create admin user
print("[1/2] Creating admin user...")
try:
    admin = create_user(
        email="admin@centef.org",
        password="Admin123!",
        full_name="CENTEF Administrator",
        roles=["admin", "user"]
    )
    print(f"✅ Admin user created:")
    print(f"   Email: {admin.email}")
    print(f"   Password: Admin123!")
    print(f"   Roles: {', '.join(admin.roles)}")
    print()
except ValueError as e:
    print(f"⚠️  Admin user already exists: {e}")
    print()

# Create regular user
print("[2/2] Creating regular user...")
try:
    user = create_user(
        email="user@centef.org",
        password="User123!",
        full_name="CENTEF User",
        roles=["user"]
    )
    print(f"✅ Regular user created:")
    print(f"   Email: {user.email}")
    print(f"   Password: User123!")
    print(f"   Roles: {', '.join(user.roles)}")
    print()
except ValueError as e:
    print(f"⚠️  Regular user already exists: {e}")
    print()

print("=" * 80)
print("Setup Complete!")
print("=" * 80)
print()
print("You can now:")
print("1. Start the API server: python apps/agent_api/main.py")
print("2. Login as admin: POST /auth/login with admin@centef.org / Admin123!")
print("3. Login as user: POST /auth/login with user@centef.org / User123!")
print()
print("Admin capabilities:")
print("  - Approve/reject documents: PUT /admin/manifest/{id}/approve")
print("  - View pending approvals: GET /admin/manifest/pending")
print("  - View system stats: GET /admin/stats")
print("  - Manage users: GET /admin/users")
print()
print("Regular user capabilities:")
print("  - Chat with RAG system: POST /chat")
print("  - View manifest: GET /manifest")
print("  - Manage own chat sessions")
print()
print("⚠️  IMPORTANT: Change these passwords in production!")
