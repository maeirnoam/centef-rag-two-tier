"""
Simple user management for CENTEF RAG system.
Stores users in GCS with password hashing.

For production, consider:
- PostgreSQL/Firestore for user data
- OAuth2 integration (Google, GitHub)
- Firebase Authentication
- Role-based access control (RBAC)
"""
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib
import secrets

from google.cloud import storage

logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
USER_DATA_BUCKET = os.getenv("USER_DATA_BUCKET", "centef-rag-bucket")
USER_DATA_PATH = os.getenv("USER_DATA_PATH", "users/users.jsonl")


@dataclass
class UserProfile:
    """User profile with authentication details."""
    user_id: str
    email: str
    hashed_password: str
    full_name: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_login: Optional[str] = None
    roles: List[str] = field(default_factory=lambda: ["user"])
    is_active: bool = True
    total_tokens: int = 0  # Total tokens used across all sessions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSONL serialization."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "hashed_password": self.hashed_password,
            "full_name": self.full_name,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "roles": self.roles,
            "is_active": self.is_active,
            "total_tokens": self.total_tokens,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """Create UserProfile from dictionary."""
        return cls(
            user_id=data["user_id"],
            email=data["email"],
            hashed_password=data["hashed_password"],
            full_name=data["full_name"],
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            last_login=data.get("last_login"),
            roles=data.get("roles", ["user"]),
            is_active=data.get("is_active", True),
            total_tokens=data.get("total_tokens", 0),
        )


def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256 with salt.
    
    NOTE: For production, use bcrypt or argon2 instead:
    - pip install bcrypt
    - import bcrypt
    - return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password with salt
    """
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password to verify
        hashed_password: Stored hash (format: salt$hash)
    
    Returns:
        True if password matches
    """
    try:
        salt, pwd_hash = hashed_password.split("$")
        test_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return test_hash == pwd_hash
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def _load_users() -> List[UserProfile]:
    """
    Load all users from GCS.
    
    Returns:
        List of UserProfile objects
    """
    try:
        client = storage.Client(project=PROJECT_ID)
        bucket_name = USER_DATA_BUCKET.replace("gs://", "")
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(USER_DATA_PATH)
        
        if not blob.exists():
            logger.info("No users file found, returning empty list")
            return []
        
        content = blob.download_as_text()
        users = []
        
        for line in content.strip().split("\n"):
            if line:
                data = json.loads(line)
                users.append(UserProfile.from_dict(data))
        
        logger.info(f"Loaded {len(users)} users")
        return users
        
    except Exception as e:
        logger.error(f"Error loading users: {e}", exc_info=True)
        return []


def _save_users(users: List[UserProfile]) -> None:
    """
    Save all users to GCS.
    
    Args:
        users: List of UserProfile objects
    """
    try:
        client = storage.Client(project=PROJECT_ID)
        bucket_name = USER_DATA_BUCKET.replace("gs://", "")
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(USER_DATA_PATH)
        
        # Write as JSONL
        content = "\n".join(json.dumps(user.to_dict()) for user in users)
        blob.upload_from_string(content, content_type="application/jsonl")
        
        logger.info(f"Saved {len(users)} users to gs://{bucket_name}/{USER_DATA_PATH}")
        
    except Exception as e:
        logger.error(f"Error saving users: {e}", exc_info=True)
        raise


def create_user(email: str, password: str, full_name: str, roles: Optional[List[str]] = None) -> UserProfile:
    """
    Create a new user.
    
    Args:
        email: User's email (used as unique identifier)
        password: Plain text password (will be hashed)
        full_name: User's full name
        roles: List of roles (default: ["user"]). Use ["admin"] for admins or ["user", "admin"] for both.
    
    Returns:
        Created UserProfile
    
    Raises:
        ValueError: If user already exists
    """
    logger.info(f"Creating user: {email} with roles: {roles}")
    
    # Load existing users
    users = _load_users()
    
    # Check if user exists
    if any(u.email == email for u in users):
        raise ValueError(f"User with email {email} already exists")
    
    # Create user ID from email
    user_id = email.split("@")[0].replace(".", "_")
    
    # Hash password
    hashed_pw = hash_password(password)
    
    # Default to user role if not specified
    if roles is None:
        roles = ["user"]
    
    # Create user
    user = UserProfile(
        user_id=user_id,
        email=email,
        hashed_password=hashed_pw,
        full_name=full_name,
        roles=roles
    )
    
    # Add to list and save
    users.append(user)
    _save_users(users)
    
    logger.info(f"User created successfully: {user_id}")
    return user


def authenticate_user(email: str, password: str) -> Optional[UserProfile]:
    """
    Authenticate a user with email and password.
    
    Args:
        email: User's email
        password: Plain text password
    
    Returns:
        UserProfile if authentication successful, None otherwise
    """
    logger.info(f"Authenticating user: {email}")
    
    users = _load_users()
    
    # Find user by email
    user = next((u for u in users if u.email == email), None)
    
    if not user:
        logger.warning(f"User not found: {email}")
        return None
    
    if not user.is_active:
        logger.warning(f"User is inactive: {email}")
        return None
    
    # Verify password
    if not verify_password(password, user.hashed_password):
        logger.warning(f"Invalid password for user: {email}")
        return None
    
    # Update last login
    user.last_login = datetime.utcnow().isoformat()
    _update_user(user)
    
    logger.info(f"User authenticated successfully: {email}")
    return user


def get_user_by_id(user_id: str) -> Optional[UserProfile]:
    """
    Get a user by their user_id.
    
    Args:
        user_id: User ID
    
    Returns:
        UserProfile if found, None otherwise
    """
    users = _load_users()
    return next((u for u in users if u.user_id == user_id), None)


def get_user_by_email(email: str) -> Optional[UserProfile]:
    """
    Get a user by their email.
    
    Args:
        email: User's email
    
    Returns:
        UserProfile if found, None otherwise
    """
    users = _load_users()
    return next((u for u in users if u.email == email), None)


def _update_user(user: UserProfile) -> None:
    """
    Update an existing user (internal function).
    
    Args:
        user: UserProfile to update
    """
    users = _load_users()
    
    # Find and replace
    for i, u in enumerate(users):
        if u.user_id == user.user_id:
            users[i] = user
            break
    
    _save_users(users)


def update_user(user: UserProfile) -> UserProfile:
    """
    Update an existing user (public function).
    
    Args:
        user: UserProfile to update
    
    Returns:
        Updated UserProfile
    """
    _update_user(user)
    return user


def update_user_password(user_id: str, new_password: str) -> bool:
    """
    Update a user's password.
    
    Args:
        user_id: User ID
        new_password: New plain text password
    
    Returns:
        True if successful
    """
    user = get_user_by_id(user_id)
    
    if not user:
        return False
    
    user.hashed_password = hash_password(new_password)
    _update_user(user)
    
    logger.info(f"Password updated for user: {user_id}")
    return True


def deactivate_user(user_id: str) -> bool:
    """
    Deactivate a user (soft delete).
    
    Args:
        user_id: User ID
    
    Returns:
        True if successful
    """
    user = get_user_by_id(user_id)
    
    if not user:
        return False
    
    user.is_active = False
    _update_user(user)
    
    logger.info(f"User deactivated: {user_id}")
    return True


def increment_user_tokens(user_id: str, tokens: int) -> bool:
    """
    Increment the total token count for a user.
    
    Args:
        user_id: User ID
        tokens: Number of tokens to add
    
    Returns:
        True if successful
    """
    user = get_user_by_id(user_id)
    
    if not user:
        logger.error(f"User not found: {user_id}")
        return False
    
    user.total_tokens += tokens
    _update_user(user)
    
    logger.info(f"User {user_id} tokens updated: +{tokens} (total: {user.total_tokens})")
    return True


def list_all_users() -> List[UserProfile]:
    """
    List all users (admin function).
    
    Returns:
        List of all UserProfile objects
    """
    return _load_users()


# CLI tool for user management
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python user_management.py create <email> <password> <full_name>")
        print("  python user_management.py list")
        print("  python user_management.py deactivate <email>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 5:
            print("Usage: python user_management.py create <email> <password> <full_name> [roles]")
            print("  roles: Optional comma-separated list (e.g., 'user' or 'admin' or 'user,admin')")
            print("  Default: 'user'")
            sys.exit(1)
        
        email = sys.argv[2]
        password = sys.argv[3]
        full_name = sys.argv[4]
        
        # Parse roles if provided
        roles = None
        if len(sys.argv) > 5:
            roles = [r.strip() for r in sys.argv[5].split(",")]
        
        try:
            user = create_user(email, password, full_name, roles=roles)
            print(f"✅ User created successfully!")
            print(f"   User ID: {user.user_id}")
            print(f"   Email: {user.email}")
            print(f"   Name: {user.full_name}")
            print(f"   Roles: {', '.join(user.roles)}")
        except ValueError as e:
            print(f"❌ Error: {e}")
    
    elif command == "list":
        users = list_all_users()
        print(f"\nTotal users: {len(users)}\n")
        for user in users:
            status = "✅ Active" if user.is_active else "❌ Inactive"
            print(f"  {user.email} ({user.user_id}) - {user.full_name} [{status}]")
            print(f"    Roles: {', '.join(user.roles)}")
            print(f"    Created: {user.created_at}")
            if user.last_login:
                print(f"    Last login: {user.last_login}")
            print()
    
    elif command == "deactivate":
        if len(sys.argv) != 3:
            print("Usage: python user_management.py deactivate <email>")
            sys.exit(1)
        
        email = sys.argv[2]
        user = get_user_by_email(email)
        
        if not user:
            print(f"❌ User not found: {email}")
            sys.exit(1)
        
        if deactivate_user(user.user_id):
            print(f"✅ User deactivated: {email}")
        else:
            print(f"❌ Failed to deactivate user")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
