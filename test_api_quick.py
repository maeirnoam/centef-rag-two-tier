"""
Quick API test with optimizations
"""
import requests
import json

API_BASE_URL = "http://localhost:8001"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJleHAiOjE3NjM1NjY0MTV9.wL_1uiN4LybWG0E90D7KJtoq0WN8A1Sk7SImSewuo4I"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Test 1: Simple query without optimizations (baseline)
print("=" * 80)
print("TEST 1: Simple AML query WITHOUT optimizations")
print("=" * 80)

request_data = {
    "query": "What is AML?"
}

response = requests.post(f"{API_BASE_URL}/chat", json=request_data, headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Answer (first 200 chars): {data['answer'][:200]}...")
    print(f"Sources: {len(data['sources'])}")
    print(f"Model: {data['model_used']}")
else:
    print(f"Error: {response.text}")

print("\n" + "=" * 80)
print("TEST 2: Same query WITH optimizations")
print("=" * 80)

request_data = {
    "query": "What is AML?",
    "use_optimizations": True,
    "enable_adaptive_limits": True,
    "enable_reranking": True,
    "enable_deduplication": True
}

response = requests.post(f"{API_BASE_URL}/chat", json=request_data, headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Answer (first 200 chars): {data['answer'][:200]}...")
    print(f"Sources: {len(data['sources'])}")
    print(f"Model: {data['model_used']}")
    
    if data.get('optimization_metadata'):
        print("\nOptimization Metadata:")
        print(json.dumps(data['optimization_metadata'], indent=2))
else:
    print(f"Error: {response.text}")

print("\n" + "=" * 80)
print("TEST 3: Outline for presentation WITH optimizations")
print("=" * 80)

request_data = {
    "query": "Help prepare an outline for presentation on recent changes in Hezbollah financing structures",
    "use_optimizations": True,
    "enable_adaptive_limits": True,
    "enable_query_expansion": True,
    "enable_reranking": True,
    "enable_deduplication": True
}

response = requests.post(f"{API_BASE_URL}/chat", json=request_data, headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Answer (first 400 chars):\n{data['answer'][:400]}...")
    print(f"\nSources: {len(data['sources'])}")
    
    if data.get('optimization_metadata'):
        format_info = data['optimization_metadata'].get('format_detection', {})
        print(f"Detected format: {format_info.get('format_type')}")
        print(f"Structure: {format_info.get('structure')}")
else:
    print(f"Error: {response.text}")

print("\n" + "=" * 80)
print("TEST 4: Blog post request WITH optimizations")
print("=" * 80)

request_data = {
    "query": "Write a blog post about the recent CENTEF events",
    "use_optimizations": True,
    "enable_adaptive_limits": True,
    "enable_query_expansion": False,
    "enable_reranking": True
}

response = requests.post(f"{API_BASE_URL}/chat", json=request_data, headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Answer (first 300 chars):\n{data['answer'][:300]}...")
    print(f"\nSources: {len(data['sources'])}")
    
    if data.get('optimization_metadata'):
        format_info = data['optimization_metadata'].get('format_detection', {})
        print(f"Detected format: {format_info.get('format_type')}")
        print(f"Length: {format_info.get('length')}")
        print(f"Max tokens: {format_info.get('max_tokens')}")
else:
    print(f"Error: {response.text}")

print("\n" + "=" * 80)
print("TEST 5: Tweet request WITH optimizations")
print("=" * 80)

request_data = {
    "query": "Write a tweet about the recent CENTEF events",
    "use_optimizations": True,
    "enable_adaptive_limits": True,
    "enable_query_expansion": False,
    "enable_reranking": True
}

response = requests.post(f"{API_BASE_URL}/chat", json=request_data, headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Tweet:\n{data['answer']}")
    print(f"\nSources: {len(data['sources'])}")
    
    if data.get('optimization_metadata'):
        format_info = data['optimization_metadata'].get('format_detection', {})
        print(f"Detected format: {format_info.get('format_type')}")
        print(f"Length: {format_info.get('length')}")
        print(f"Max tokens: {format_info.get('max_tokens')}")
else:
    print(f"Error: {response.text}")

print("\n✓ Tests completed!")
