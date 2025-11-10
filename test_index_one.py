"""
Test indexing a single document with the new struct_data format.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import get_manifest_entries, DocumentStatus
from services.embedding.index_documents import index_document

# Get a document that's ready to index (or embedded)
entries = get_manifest_entries()

# Look for documents with pending_approval status (or embedded to re-test)
test_candidates = []
for entry in entries:
    if entry.status in [DocumentStatus.PENDING_EMBEDDING.value, DocumentStatus.EMBEDDED.value, DocumentStatus.PENDING_APPROVAL.value]:
        if entry.data_path and entry.summary_path:
            test_candidates.append(entry)

if not test_candidates:
    print("❌ No suitable documents found to test indexing")
    print("   Need documents with status: pending_embedding, embedded, or pending_approval")
    print("   And both data_path and summary_path must be set")
    sys.exit(1)

print(f"Found {len(test_candidates)} documents available for testing:")
for i, entry in enumerate(test_candidates[:5], 1):  # Show first 5
    print(f"  {i}. {entry.source_id} - {entry.filename} (status: {entry.status})")

# Use the first one
entry = test_candidates[0]

print(f"\n{'='*80}")
print(f"Testing indexing for: {entry.source_id}")
print(f"Filename: {entry.filename}")
print(f"Current status: {entry.status}")
print(f"Chunks path: {entry.data_path}")
print(f"Summary path: {entry.summary_path}")
print(f"{'='*80}\n")

proceed = input("Proceed with indexing test? (yes/no): ").strip().lower()
if proceed not in ['yes', 'y']:
    print("Cancelled.")
    sys.exit(0)

print("\nStarting indexing test...")
try:
    result = index_document(entry)
    
    print(f"\n{'='*80}")
    print("INDEXING RESULT:")
    print(f"{'='*80}")
    print(f"Success: {result['success']}")
    
    if result['chunks']:
        print(f"\nChunks:")
        print(f"  Total: {result['chunks'].get('total', 0)}")
        print(f"  Succeeded: {result['chunks'].get('success', 0)}")
        print(f"  Failed: {result['chunks'].get('failed', 0)}")
        if result['chunks'].get('errors'):
            print(f"  Errors:")
            for err in result['chunks']['errors'][:3]:  # Show first 3 errors
                print(f"    - {err}")
    
    if result['summary']:
        print(f"\nSummary:")
        print(f"  Success: {result['summary'].get('success', False)}")
        if result['summary'].get('error'):
            print(f"  Error: {result['summary']['error']}")
    
    if result['error']:
        print(f"\nOverall Error: {result['error']}")
    
    print(f"\n{'='*80}\n")
    
    if result['success']:
        print("✅ Indexing test PASSED - struct_data format is working!")
    else:
        print("❌ Indexing test FAILED - check errors above")
        
except Exception as e:
    print(f"\n❌ Exception during indexing: {e}")
    import traceback
    traceback.print_exc()
