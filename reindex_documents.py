"""
Re-index documents script.
Resets document status and re-indexes to Discovery Engine with fixes.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import get_manifest_entries, update_manifest_entry
from services.embedding.index_documents import index_document

print("="*80)
print("  Re-indexing Documents to Discovery Engine")
print("="*80)
print()

# Get all documents that are ready or already indexed
entries = get_manifest_entries()

# Filter for documents that have been processed and have data
ready_entries = [
    e for e in entries 
    if e.status.value in ['ready', 'pending_embedding'] 
    and e.data_path 
    and e.summary_path
]

print(f"Found {len(ready_entries)} documents ready for indexing:")
for entry in ready_entries:
    print(f"  - {entry.source_id}: {entry.title}")

print()

if not ready_entries:
    print("⚠️  No documents found with status 'ready' or 'pending_embedding'")
    print("   Make sure documents have been processed first.")
    sys.exit(0)

# Ask for confirmation
response = input(f"\nRe-index {len(ready_entries)} documents? (yes/no): ").strip().lower()

if response not in ['yes', 'y']:
    print("Cancelled.")
    sys.exit(0)

print()
print("="*80)
print("Starting re-indexing...")
print("="*80)
print()

success_count = 0
failed_count = 0

for i, entry in enumerate(ready_entries, 1):
    print(f"\n[{i}/{len(ready_entries)}] Processing: {entry.source_id}")
    print(f"  Title: {entry.title}")
    
    try:
        # Reset to pending_embedding if it's already ready
        if entry.status.value == 'ready':
            print(f"  Resetting status to pending_embedding...")
            update_manifest_entry(entry.source_id, {'status': 'pending_embedding'})
        
        # Index the document
        print(f"  Indexing chunks and summary...")
        index_document(entry)
        
        # Update status to ready
        print(f"  Updating status to ready...")
        update_manifest_entry(entry.source_id, {'status': 'ready'})
        
        print(f"  ✅ Successfully indexed")
        success_count += 1
        
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        failed_count += 1
        
        # Ask if we should continue
        if failed_count < 3:
            continue_response = input(f"  Continue with remaining documents? (yes/no): ").strip().lower()
            if continue_response not in ['yes', 'y']:
                print("\nStopping re-index process.")
                break

print()
print("="*80)
print("  Re-indexing Complete")
print("="*80)
print(f"  ✅ Successfully indexed: {success_count}")
print(f"  ❌ Failed: {failed_count}")
print(f"  Total: {success_count + failed_count}/{len(ready_entries)}")
print()

if success_count > 0:
    print("✅ Documents have been re-indexed with the fixes!")
    print("   You can now test the search again with:")
    print("   python quick_test.py")
