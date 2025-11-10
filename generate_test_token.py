"""
Generate authentication tokens for testing the CENTEF RAG API.

Usage:
    python generate_test_token.py [user_id] [email]

Examples:
    python generate_test_token.py
    python generate_test_token.py john_doe john@example.com
    python generate_test_token.py --api-key user123
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.auth import generate_test_token, create_api_key

def main():
    """Generate test authentication credentials."""
    print("=" * 80)
    print("CENTEF RAG API - Authentication Token Generator")
    print("=" * 80)
    print()
    
    # Parse command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--api-key":
        # Generate API key
        user_id = sys.argv[2] if len(sys.argv) > 2 else "test_user"
        api_key = create_api_key(user_id)
        
        print("API Key Generated:")
        print(f"  User ID: {user_id}")
        print(f"  API Key: {api_key}")
        print()
        print("Usage:")
        print(f"  Add to .env file: VALID_API_KEYS={api_key}")
        print(f"  Use in requests: X-API-Key: {api_key}")
        print()
        print("Example curl command:")
        print(f'  curl -H "X-API-Key: {api_key}" http://localhost:8080/chat/sessions')
        
    else:
        # Generate JWT token
        user_id = sys.argv[1] if len(sys.argv) > 1 else "test_user"
        email = sys.argv[2] if len(sys.argv) > 2 else "test@example.com"
        
        token = generate_test_token(user_id, email)
        
        print("JWT Token Generated:")
        print(f"  User ID: {user_id}")
        print(f"  Email: {email}")
        print(f"  Token: {token}")
        print()
        print("Usage:")
        print(f'  Authorization: Bearer {token}')
        print()
        print("Example curl command:")
        print(f'  curl -H "Authorization: Bearer {token}" http://localhost:8080/chat/sessions')
        print()
        print("Example Python requests:")
        print(f'''
import requests

headers = {{"Authorization": f"Bearer {token}"}}
response = requests.get("http://localhost:8080/chat/sessions", headers=headers)
print(response.json())
        '''.strip())
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
