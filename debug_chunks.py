"""
Debug script to investigate chunk search issues.
"""
import os
from dotenv import load_dotenv
from google.cloud import discoveryengine_v1beta as discoveryengine

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
VERTEX_SEARCH_LOCATION = os.getenv("VERTEX_SEARCH_LOCATION", "global")
CHUNKS_DATASTORE_ID = os.getenv("CHUNKS_DATASTORE_ID")

print(f"Project ID: {PROJECT_ID}")
print(f"Location: {VERTEX_SEARCH_LOCATION}")
print(f"Chunks Datastore ID: {CHUNKS_DATASTORE_ID}")
print()

# Try a simple search
client = discoveryengine.SearchServiceClient()

serving_config = (
    f"projects/{PROJECT_ID}/"
    f"locations/{VERTEX_SEARCH_LOCATION}/"
    f"collections/default_collection/"
    f"dataStores/{CHUNKS_DATASTORE_ID}/"
    f"servingConfigs/default_config"
)

print(f"Serving config: {serving_config}")
print()

# Try with wildcard query to get ANY results
print("Testing with wildcard query '*' to get any documents...")
request = discoveryengine.SearchRequest(
    serving_config=serving_config,
    query="*",
    page_size=5,
)

try:
    response = client.search(request=request)
    
    results = list(response.results)
    print(f"\nFound {len(results)} results with wildcard query")
    
    if results:
        print("\nFirst result structure:")
        first = results[0]
        print(f"  ID: {first.document.id}")
        print(f"  Name: {first.document.name}")
        print(f"  Has struct_data: {bool(first.document.struct_data)}")
        
        if first.document.struct_data:
            print(f"\n  struct_data keys: {list(first.document.struct_data.keys())}")
            struct_data = dict(first.document.struct_data)
            print(f"\n  Sample data:")
            for key, value in list(struct_data.items())[:5]:
                if isinstance(value, str) and len(value) > 100:
                    print(f"    {key}: {value[:100]}...")
                else:
                    print(f"    {key}: {value}")
    else:
        print("\n⚠️  No results found even with wildcard!")
        print("This suggests the datastore might be empty or not properly indexed.")
        
except Exception as e:
    print(f"\n❌ Error: {e}")

# Try a specific search query
print("\n" + "="*80)
print("Testing with specific query 'CTF'...")
request = discoveryengine.SearchRequest(
    serving_config=serving_config,
    query="CTF",
    page_size=5,
)

try:
    response = client.search(request=request)
    results = list(response.results)
    print(f"Found {len(results)} results with 'CTF' query")
    
    if results:
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] ID: {result.document.id}")
            struct_data = dict(result.document.struct_data) if result.document.struct_data else {}
            print(f"    Title: {struct_data.get('title', 'N/A')}")
            print(f"    Source ID: {struct_data.get('source_id', 'N/A')}")
            if struct_data.get('content'):
                print(f"    Content preview: {struct_data['content'][:100]}...")
                
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "="*80)
print("Testing with 'what is' query...")
request = discoveryengine.SearchRequest(
    serving_config=serving_config,
    query="what is",
    page_size=5,
)

try:
    response = client.search(request=request)
    results = list(response.results)
    print(f"Found {len(results)} results with 'what is' query")
    
    if results:
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] ID: {result.document.id}")
            struct_data = dict(result.document.struct_data) if result.document.struct_data else {}
            print(f"    Title: {struct_data.get('title', 'N/A')}")
            
except Exception as e:
    print(f"\n❌ Error: {e}")
