"""
Purge all documents from both datastores (chunks and summaries).
"""
import os
import sys
from dotenv import load_dotenv
from google.cloud import discoveryengine_v1beta as discoveryengine

load_dotenv()

PROJECT_ID = os.getenv('PROJECT_ID')
VERTEX_SEARCH_LOCATION = os.getenv('VERTEX_SEARCH_LOCATION', 'global')
CHUNKS_DATASTORE_ID = os.getenv('CHUNKS_DATASTORE_ID')
SUMMARIES_DATASTORE_ID = os.getenv('SUMMARIES_DATASTORE_ID')

print("="*80)
print("⚠️  PURGE ALL DATASTORES ⚠️")
print("="*80)
print(f"Project: {PROJECT_ID}")
print(f"Location: {VERTEX_SEARCH_LOCATION}")
print(f"Chunks Datastore: {CHUNKS_DATASTORE_ID}")
print(f"Summaries Datastore: {SUMMARIES_DATASTORE_ID}")
print()

response = input("⚠️  This will DELETE ALL documents from BOTH datastores. Continue? (type 'DELETE' to confirm): ").strip()

if response != 'DELETE':
    print("Cancelled.")
    sys.exit(0)

client = discoveryengine.DocumentServiceClient()

# Purge chunks
print()
print("="*80)
print("Purging CHUNKS datastore...")
print("="*80)

chunks_parent = (
    f"projects/{PROJECT_ID}/"
    f"locations/{VERTEX_SEARCH_LOCATION}/"
    f"collections/default_collection/"
    f"dataStores/{CHUNKS_DATASTORE_ID}/"
    f"branches/default_branch"
)

try:
    request = discoveryengine.ListDocumentsRequest(
        parent=chunks_parent,
        page_size=1000
    )
    
    chunks_docs = list(client.list_documents(request=request))
    print(f"Found {len(chunks_docs)} chunks to delete")
    
    deleted_count = 0
    failed_count = 0
    
    for i, doc in enumerate(chunks_docs, 1):
        try:
            request = discoveryengine.DeleteDocumentRequest(name=doc.name)
            client.delete_document(request=request)
            deleted_count += 1
            
            if i % 50 == 0:
                print(f"  Deleted {i}/{len(chunks_docs)} chunks...")
                
        except Exception as e:
            print(f"  ❌ Failed to delete {doc.name.split('/')[-1]}: {e}")
            failed_count += 1
    
    print(f"\n✅ Deleted {deleted_count} chunks")
    if failed_count > 0:
        print(f"❌ Failed {failed_count} chunks")
    
except Exception as e:
    print(f"❌ Error purging chunks: {e}")

# Purge summaries
print()
print("="*80)
print("Purging SUMMARIES datastore...")
print("="*80)

summaries_parent = (
    f"projects/{PROJECT_ID}/"
    f"locations/{VERTEX_SEARCH_LOCATION}/"
    f"collections/default_collection/"
    f"dataStores/{SUMMARIES_DATASTORE_ID}/"
    f"branches/default_branch"
)

try:
    request = discoveryengine.ListDocumentsRequest(
        parent=summaries_parent,
        page_size=1000
    )
    
    summaries_docs = list(client.list_documents(request=request))
    print(f"Found {len(summaries_docs)} summaries to delete")
    
    deleted_count = 0
    failed_count = 0
    
    for i, doc in enumerate(summaries_docs, 1):
        try:
            request = discoveryengine.DeleteDocumentRequest(name=doc.name)
            client.delete_document(request=request)
            deleted_count += 1
            
            if i % 10 == 0:
                print(f"  Deleted {i}/{len(summaries_docs)} summaries...")
                
        except Exception as e:
            print(f"  ❌ Failed to delete {doc.name.split('/')[-1]}: {e}")
            failed_count += 1
    
    print(f"\n✅ Deleted {deleted_count} summaries")
    if failed_count > 0:
        print(f"❌ Failed {failed_count} summaries")
    
except Exception as e:
    print(f"❌ Error purging summaries: {e}")

# Reset manifest statuses
print()
print("="*80)
print("Resetting manifest statuses to pending_embedding...")
print("="*80)

from shared.manifest import get_manifest_entries, update_manifest_entry

entries = get_manifest_entries()
updated = 0

for entry in entries:
    if entry.status in ['embedded', 'error']:
        try:
            update_manifest_entry(entry.source_id, {'status': 'pending_embedding'})
            print(f"  ✅ Reset {entry.source_id}")
            updated += 1
        except Exception as e:
            print(f"  ⚠️  Could not reset {entry.source_id}: {e}")

print(f"\n✅ Reset {updated} manifest entries")

print()
print("="*80)
print("PURGE COMPLETE")
print("="*80)
print()
print("You can now re-index all documents with:")
print("  python index_all_pending.py")
