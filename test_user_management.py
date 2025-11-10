"""
Test script for user management endpoints.
Run backend first: cd apps/agent_api && python main.py
"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Use admin credentials
ADMIN_EMAIL = "admin@centef.org"
ADMIN_PASSWORD = "Admin123!"

def login():
    """Login and get JWT token."""
    print("Logging in as admin...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Logged in successfully as {data['email']}")
        return data['access_token']
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None

def test_list_users(token):
    """Test GET /admin/users"""
    print("\n📋 Testing: List all users")
    response = requests.get(
        f"{BASE_URL}/admin/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        users = response.json()
        print(f"✅ Found {len(users)} users:")
        for user in users:
            roles = ", ".join(user['roles'])
            status = "Active" if user['is_active'] else "Inactive"
            print(f"  • {user['email']} ({roles}) - {status}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)

def test_create_user(token):
    """Test POST /admin/users"""
    print("\n➕ Testing: Create new user")
    
    test_user = {
        "email": "testuser@example.com",
        "password": "TestPass123!",
        "full_name": "Test User",
        "roles": ["user"]
    }
    
    response = requests.post(
        f"{BASE_URL}/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json=test_user
    )
    
    if response.status_code == 201:
        data = response.json()
        print(f"✅ User created: {data['user']['email']} (ID: {data['user']['user_id']})")
        return data['user']['user_id']
    elif response.status_code == 409:
        print(f"⚠️  User already exists (this is OK for testing)")
        # Get the user_id by listing users
        list_response = requests.get(
            f"{BASE_URL}/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        users = list_response.json()
        for user in users:
            if user['email'] == test_user['email']:
                return user['user_id']
        return None
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)
        return None

def test_update_user(token, user_id):
    """Test PUT /admin/users/{user_id}"""
    print(f"\n✏️  Testing: Update user {user_id}")
    
    update_data = {
        "full_name": "Test User Updated",
        "roles": ["user", "admin"],
        "is_active": True
    }
    
    response = requests.put(
        f"{BASE_URL}/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json=update_data
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ User updated: {data['user']['full_name']}")
        print(f"   Roles: {', '.join(data['user']['roles'])}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)

def test_reset_password(token, user_id):
    """Test password reset via PUT /admin/users/{user_id}"""
    print(f"\n🔑 Testing: Reset password for {user_id}")
    
    response = requests.put(
        f"{BASE_URL}/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"password": "NewPassword123!"}
    )
    
    if response.status_code == 200:
        print(f"✅ Password reset successfully")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)

def test_delete_user(token, user_id):
    """Test DELETE /admin/users/{user_id}"""
    print(f"\n🗑️  Testing: Delete user {user_id}")
    
    response = requests.delete(
        f"{BASE_URL}/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ User deactivated: {data['message']}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)

def main():
    print("=" * 60)
    print("User Management Endpoints Test")
    print("=" * 60)
    
    # Login
    token = login()
    if not token:
        print("\n❌ Cannot proceed without authentication")
        return
    
    # Test list users
    test_list_users(token)
    
    # Test create user
    user_id = test_create_user(token)
    
    if user_id:
        # Test update user
        test_update_user(token, user_id)
        
        # Test password reset
        test_reset_password(token, user_id)
        
        # Test delete user
        test_delete_user(token, user_id)
        
        # Verify deletion
        print("\n🔍 Verifying deletion...")
        test_list_users(token)
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
