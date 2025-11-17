"""Minimal test - just check if service is responding"""
import requests

url = "http://127.0.0.1:8080"
api_key = "local-test-key-12345"

print("Testing external YouTube downloader service...")
print(f"URL: {url}")
print()

try:
    # Test 1: Root endpoint
    print("[1/2] Testing root endpoint...")
    r = requests.get(f"{url}/")
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    print("  ✓ Root endpoint works")
    print()
    
    # Test 2: Health endpoint  
    print("[2/2] Testing health endpoint...")
    r = requests.get(f"{url}/health")
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    print("  ✓ Health endpoint works")
    print()
    
    print("✓ External service is responding correctly!")
    print()
    print("Service is ready. You can now test the full pipeline.")
    
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to service")
    print()
    print("Make sure the service is running:")
    print("  1. Open the Python terminal")
    print("  2. Verify it shows: 'Uvicorn running on http://127.0.0.1:8080'")
    print("  3. Keep that terminal open")
    
except Exception as e:
    print(f"❌ Error: {e}")
