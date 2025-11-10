"""
Authentication utilities for CENTEF RAG API.
Provides user authentication and authorization.
"""
import logging
import os
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Environment variables
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# API Key for simple authentication (fallback)
API_KEY_HEADER = os.getenv("API_KEY_HEADER", "X-API-Key")
VALID_API_KEYS = os.getenv("VALID_API_KEYS", "").split(",") if os.getenv("VALID_API_KEYS") else []

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


class User(BaseModel):
    """User model."""
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    roles: list[str] = []


class TokenData(BaseModel):
    """JWT token data."""
    user_id: str
    email: Optional[str] = None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
    
    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        
        if user_id is None:
            return None
        
        return TokenData(user_id=user_id, email=email)
        
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None


def verify_api_key(api_key: str) -> Optional[str]:
    """
    Verify an API key.
    
    Args:
        api_key: API key to verify
    
    Returns:
        User ID if valid, None otherwise
    """
    if api_key in VALID_API_KEYS:
        # Extract user_id from API key (format: userid_randomstring)
        # Or use a mapping/database lookup
        # For now, use the API key itself as user_id
        return f"apikey_{api_key[:8]}"
    
    return None


async def get_current_user(
    bearer_credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header)
) -> User:
    """
    Get the current authenticated user.
    
    Supports both JWT bearer tokens and API keys.
    
    Args:
        bearer_credentials: Bearer token credentials
        api_key: API key from header
    
    Returns:
        User object
    
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try JWT token first
    if bearer_credentials:
        token = bearer_credentials.credentials
        token_data = verify_token(token)
        
        if token_data:
            # Get user profile from database to retrieve actual roles
            from shared.user_management import get_user_by_id
            user_profile = get_user_by_id(token_data.user_id)
            
            if user_profile:
                return User(
                    user_id=user_profile.user_id,
                    email=user_profile.email,
                    name=user_profile.full_name,
                    roles=user_profile.roles
                )
            else:
                # User not found in database, return with default role
                return User(
                    user_id=token_data.user_id,
                    email=token_data.email,
                    roles=["user"]
                )
    
    # Try API key
    if api_key:
        user_id = verify_api_key(api_key)
        if user_id:
            return User(
                user_id=user_id,
                roles=["user"]
            )
    
    # No valid authentication found
    raise credentials_exception


async def get_optional_user(
    bearer_credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header)
) -> Optional[User]:
    """
    Get the current user if authenticated, otherwise return None.
    
    Useful for endpoints that work with or without authentication.
    
    Args:
        bearer_credentials: Bearer token credentials
        api_key: API key from header
    
    Returns:
        User object or None
    """
    try:
        return await get_current_user(bearer_credentials, api_key)
    except HTTPException:
        return None


def require_role(required_role: str):
    """
    Dependency that requires a specific role.
    
    Usage:
        @app.get("/admin/users")
        async def list_users(current_user: User = Depends(require_role("admin"))):
            # Only admins can access this
            ...
    
    Args:
        required_role: Role required to access the endpoint
    
    Returns:
        Dependency function
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if required_role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        return current_user
    
    return role_checker


def require_any_role(required_roles: List[str]):
    """
    Dependency that requires at least one of the specified roles.
    
    Usage:
        @app.get("/documents")
        async def list_docs(current_user: User = Depends(require_any_role(["admin", "editor"]))):
            # Admins or editors can access this
            ...
    
    Args:
        required_roles: List of roles, user must have at least one
    
    Returns:
        Dependency function
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(required_roles)}"
            )
        return current_user
    
    return role_checker


# Simple development mode: generate test token
def generate_test_token(user_id: str = "test_user", email: str = "test@example.com") -> str:
    """
    Generate a test JWT token for development.
    
    Args:
        user_id: User ID
        email: User email
    
    Returns:
        JWT token
    """
    token_data = {
        "sub": user_id,
        "email": email
    }
    return create_access_token(token_data)


# For testing/development: create a simple API key validator
def create_api_key(user_id: str) -> str:
    """
    Create a simple API key for development.
    
    In production, use a proper key generation and storage system.
    
    Args:
        user_id: User ID
    
    Returns:
        API key
    """
    import hashlib
    import secrets
    
    random_part = secrets.token_urlsafe(16)
    api_key = f"{user_id}_{random_part}"
    
    logger.info(f"Generated API key for user {user_id}: {api_key}")
    logger.warning("Add this to VALID_API_KEYS environment variable")
    
    return api_key
