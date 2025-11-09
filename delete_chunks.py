"""
Delete documents from chunks datastore to prepare for re-indexing.
Can delete all chunks or just specific source_ids.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import discoveryengine_v1beta as discoveryengine

# Load environment
load_dotenv()

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import get_manifest_entries, update_manifest_entry

PROJECT_ID = os.getenv("PROJECT_ID")
VERTEX_SEARCH_LOCATION = os.getenv("VERTEX_SEARCH_LOCATION", "global")
CHUNKS_DATASTORE_ID = os.getenv("CHUNKS_DATASTORE_ID")

print("="*80)
print("  Delete Chunks from Datastore")
print("="*80)
print()
print(f"Project: {PROJECT_ID}")
print(f"Location: {VERTEX_SEARCH_LOCATION}")
print(f"Chunks Datastore: {CHUNKS_DATASTORE_ID}")
print()

# Ask if selective or all
print("Options:")
print("  1. Delete ALL chunks (entire datastore)")
print("  2. Delete chunks for specific source_ids")
print()
choice = input("Enter choice (1 or 2): ").strip()

source_ids_to_delete = []

if choice == "2":
    print()
    print("Enter source_ids to delete (one per line, empty line to finish):")
    while True:
        source_id = input("> ").strip()
        if not source_id:
            break
        source_ids_to_delete.append(source_id)
    
    if not source_ids_to_delete:
        print("No source_ids provided. Exiting.")
        sys.exit(0)
    
    print()
    print(f"Will delete chunks for {len(source_ids_to_delete)} source_ids:")
    for sid in source_ids_to_delete:
        print(f"  - {sid}")
elif choice != "1":
    print("Invalid choice. Exiting.")
    sys.exit(1)

# Build parent path
parent = (
    f"projects/{PROJECT_ID}/"
    f"locations/{VERTEX_SEARCH_LOCATION}/"
    f"collections/default_collection/"
    f"dataStores/{CHUNKS_DATASTORE_ID}/"
    f"branches/default_branch"
)

print()

# Confirm
if choice == "1":
    response = input("⚠️  This will DELETE ALL documents from the chunks datastore. Continue? (yes/no): ").strip().lower()
else:
    response = input(f"⚠️  This will delete chunks for {len(source_ids_to_delete)} source_ids. Continue? (yes/no): ").strip().lower()

if response not in ['yes', 'y']:
    print("Cancelled.")
    sys.exit(0)

print()
print("Listing documents...")

# Initialize client
client = discoveryengine.DocumentServiceClient()

# Build parent path
parent = (
    f"projects/{PROJECT_ID}/"
    f"locations/{VERTEX_SEARCH_LOCATION}/"
    f"collections/default_collection/"
    f"dataStores/{CHUNKS_DATASTORE_ID}/"
    f"branches/default_branch"
)

# List all documents
try:
    request = discoveryengine.ListDocumentsRequest(
        parent=parent,
        page_size=1000
    )
    
    all_docs = []
    page_result = client.list_documents(request=request)
    
    for doc in page_result:
        # If selective delete, check if document belongs to one of the source_ids
        if choice == "2":
            # Document ID format is typically: source_id_page_X or source_id_chunk_X
            doc_id = doc.name.split('/')[-1]
            
            # Check if this doc belongs to any of our source_ids
            matches = False
            for source_id in source_ids_to_delete:
                if doc_id.startswith(source_id):
                    matches = True
                    break
            
            if matches:
                all_docs.append(doc.name)
        else:
            all_docs.append(doc.name)
    
    print(f"Found {len(all_docs)} documents to delete")
    
    if len(all_docs) == 0:
        print("No documents to delete.")
        sys.exit(0)
    
    print()
    print("Deleting documents...")
    
    deleted_count = 0
    failed_count = 0
    
    for i, doc_name in enumerate(all_docs, 1):
        try:
            request = discoveryengine.DeleteDocumentRequest(
                name=doc_name
            )
            client.delete_document(request=request)
            deleted_count += 1
            
            if i % 10 == 0:
                print(f"  Deleted {i}/{len(all_docs)} documents...")
                
        except Exception as e:
            print(f"  ❌ Failed to delete {doc_name}: {e}")
            failed_count += 1
    
    print()
    print("="*80)
    print(f"✅ Deleted {deleted_count} documents")
    if failed_count > 0:
        print(f"❌ Failed {failed_count} documents")
    
    # Update manifest status to pending_embedding
    if choice == "2":
        print()
        print("Updating manifest status to pending_embedding...")
        for source_id in source_ids_to_delete:
            try:
                update_manifest_entry(source_id, {'status': 'pending_embedding'})
                print(f"  ✅ Updated {source_id}")
            except Exception as e:
                print(f"  ⚠️  Could not update {source_id}: {e}")
    else:
        print()
        print("Updating manifest status for all documents to pending_embedding...")
        entries = get_manifest_entries()
        updated = 0
        for entry in entries:
            if entry.data_path:  # Only update if it has chunks
                try:
                    update_manifest_entry(entry.source_id, {'status': 'pending_embedding'})
                    updated += 1
                except Exception as e:
                    print(f"  ⚠️  Could not update {entry.source_id}: {e}")
        print(f"  ✅ Updated {updated} manifest entries")
    
    print("="*80)
    print()
    print("You can now re-index documents with:")
    if choice == "2":
        print(f"  python services/embedding/index_documents.py --source-id <source_id>")
    else:
        print("  python reindex_documents.py")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
