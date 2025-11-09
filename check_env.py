"""
Quick environment validation script.
Checks if all required environment variables are set and GCP auth is working.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from {env_path}\n")
else:
    print(f"⚠️  No .env file found at {env_path}")
    print("   Create one from .env.example\n")

# Required environment variables
required_vars = {
    "PROJECT_ID": "Your GCP project ID",
    "CHUNKS_DATASTORE_ID": "Chunks datastore ID (with _gcs_store suffix)",
    "SUMMARIES_DATASTORE_ID": "Summaries datastore ID (with _gcs_store suffix)",
    "VERTEX_SEARCH_LOCATION": "Search location (usually 'global')",
}

print("=" * 80)
print("  Environment Variable Check")
print("=" * 80)

all_set = True
for var, description in required_vars.items():
    value = os.getenv(var)
    if value:
        display = value if len(value) < 50 else value[:47] + "..."
        print(f"✅ {var:30s} = {display}")
    else:
        print(f"❌ {var:30s} = NOT SET ({description})")
        all_set = False

print()

# Test GCP authentication
print("=" * 80)
print("  Google Cloud Authentication Check")
print("=" * 80)

try:
    from google.cloud import discoveryengine_v1beta as discoveryengine
    
    # Try to create a client (will fail if auth is not set up)
    client = discoveryengine.SearchServiceClient()
    print("✅ Discovery Engine client created successfully")
    print("✅ Authentication is working")
    
except Exception as e:
    print(f"❌ Authentication error: {e}")
    print("\nTo fix authentication:")
    print("  1. Run: gcloud auth application-default login")
    print("  2. Or set: $env:GOOGLE_APPLICATION_CREDENTIALS='path\\to\\service-account.json'")

print()

# Summary
print("=" * 80)
print("  Summary")
print("=" * 80)

if all_set:
    print("✅ All environment variables are set")
    print("\nYou can now run:")
    print("  python test_search.py")
else:
    print("⚠️  Some environment variables are missing")
    print("\nPlease create a .env file with all required variables")
    print("See .env.example for a template")

print("=" * 80)
