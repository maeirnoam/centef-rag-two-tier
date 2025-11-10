"""
Create sample users for CENTEF RAG system.
Run this to ensure admin and regular user accounts exist.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.user_management import create_user, get_user_by_email

def main():
    print("Creating sample users...")
    
    # Sample users
    users = [
        {
            "email": "admin@centef.org",
            "password": "Admin123!",
            "full_name": "Admin User",
            "roles": ["user", "admin"]
        },
        {
            "email": "user@centef.org",
            "password": "User123!",
            "full_name": "Regular User",
            "roles": ["user"]
        }
    ]
    
    for user_data in users:
        try:
            # Check if user already exists
            existing = get_user_by_email(user_data["email"])
            if existing:
                print(f"✓ User already exists: {user_data['email']} (roles: {existing.roles})")
            else:
                # Create user
                user = create_user(
                    email=user_data["email"],
                    password=user_data["password"],
                    full_name=user_data["full_name"],
                    roles=user_data["roles"]
                )
                print(f"✓ Created user: {user_data['email']} (roles: {user.roles})")
        except Exception as e:
            print(f"✗ Error with {user_data['email']}: {e}")
    
    print("\nSample users ready!")
    print("\nAdmin login:")
    print("  Email: admin@centef.org")
    print("  Password: Admin123!")
    print("\nRegular user login:")
    print("  Email: user@centef.org")
    print("  Password: User123!")

if __name__ == "__main__":
    main()
