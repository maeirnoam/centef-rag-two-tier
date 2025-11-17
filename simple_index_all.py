"""
Simple script to index all embedded documents.
No emojis to avoid encoding issues.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import get_manifest_entries, update_manifest_entry
from services.embedding.index_documents import index_document

# Get all documents with status 'embedded' that have chunks
entries = [e for e in get_manifest_entries() if e.status == 'embedded' and e.data_path]

print("\n" + "="*80)
print(f"Found {len(entries)} documents with chunks to index")
print("="*80 + "\n")

for entry in entries:
    print(f"  - {entry.source_id}: {entry.title}")

if not entries:
    print("No documents to index.")
    sys.exit(0)

print("\n" + "="*80)
print("Starting indexing...")
print("="*80 + "\n")

# Index each document
results = []
for i, entry in enumerate(entries, 1):
    print(f"\n[{i}/{len(entries)}] Indexing {entry.source_id}")
    print("-"*80)

    try:
        result = index_document(entry)
        results.append(result)

        if result['success']:
            print(f"SUCCESS - Chunks: {result.get('chunks', {}).get('success', 0)}/{result.get('chunks', {}).get('total', 0)}")
        else:
            print(f"FAILED: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        results.append({
            'source_id': entry.source_id,
            'success': False,
            'error': str(e)
        })

# Print summary
print("\n" + "="*80)
print("INDEXING SUMMARY")
print("="*80)

successful = [r for r in results if r['success']]
failed = [r for r in results if not r['success']]

print(f"\nTotal documents: {len(results)}")
print(f"Successful: {len(successful)}")
print(f"Failed: {len(failed)}")

if failed:
    print("\nFailed documents:")
    for r in failed:
        print(f"  - {r['source_id']}: {r.get('error', 'Unknown error')[:100]}")

# Chunk statistics
total_chunks = sum(r.get('chunks', {}).get('total', 0) for r in results if r.get('chunks'))
success_chunks = sum(r.get('chunks', {}).get('success', 0) for r in results if r.get('chunks'))
failed_chunks = sum(r.get('chunks', {}).get('failed', 0) for r in results if r.get('chunks'))

if total_chunks > 0:
    print(f"\nChunk statistics:")
    print(f"  Total: {total_chunks}")
    print(f"  Success: {success_chunks}")
    print(f"  Failed: {failed_chunks}")

print("\n" + "="*80)
print("Done!")
print("="*80 + "\n")
