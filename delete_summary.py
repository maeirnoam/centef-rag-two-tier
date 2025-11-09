"""
Delete specific summary documents from the summaries datastore.
"""

import os
import sys
from dotenv import load_dotenv
from google.cloud import discoveryengine_v1beta as discoveryengine

# Load environment variables
load_dotenv()

# Configuration
PROJECT_ID = os.getenv('PROJECT_ID')
VERTEX_SEARCH_LOCATION = os.getenv('VERTEX_SEARCH_LOCATION', 'global')
SUMMARIES_DATASTORE_ID = os.getenv('SUMMARIES_DATASTORE_ID')

print("="*80)
print("Delete Summary Documents")
print("="*80)
print(f"Project: {PROJECT_ID}")
print(f"Location: {VERTEX_SEARCH_LOCATION}")
print(f"Summaries Datastore: {SUMMARIES_DATASTORE_ID}")
print()

# Get source_id to delete
source_id = input("Enter source_id to delete summary for (or 'all' to delete all summaries): ").strip()

if not source_id:
    print("No source_id provided. Exiting.")
    sys.exit(0)

# Initialize client
client = discoveryengine.DocumentServiceClient()

# Build parent path
parent = (
    f"projects/{PROJECT_ID}/"
    f"locations/{VERTEX_SEARCH_LOCATION}/"
    f"collections/default_collection/"
    f"dataStores/{SUMMARIES_DATASTORE_ID}/"
    f"branches/default_branch"
)

print()
print("Listing documents...")

try:
    request = discoveryengine.ListDocumentsRequest(
        parent=parent,
        page_size=1000
    )
    
    all_docs = []
    page_result = client.list_documents(request=request)
    
    for doc in page_result:
        doc_id = doc.name.split('/')[-1]
        
        if source_id == 'all':
            all_docs.append(doc.name)
        elif doc_id == source_id or doc_id.startswith(f"{source_id}_"):
            all_docs.append(doc.name)
    
    print(f"Found {len(all_docs)} summary document(s) to delete")
    
    if len(all_docs) == 0:
        print("No documents found to delete.")
        sys.exit(0)
    
    # Show documents
    print()
    print("Documents to delete:")
    for doc_name in all_docs:
        print(f"  - {doc_name.split('/')[-1]}")
    
    print()
    response = input("⚠️  Delete these summary documents? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("Cancelled.")
        sys.exit(0)
    
    print()
    print("Deleting documents...")
    
    deleted_count = 0
    failed_count = 0
    
    for doc_name in all_docs:
        try:
            request = discoveryengine.DeleteDocumentRequest(
                name=doc_name
            )
            client.delete_document(request=request)
            deleted_count += 1
            print(f"  ✅ Deleted {doc_name.split('/')[-1]}")
                
        except Exception as e:
            print(f"  ❌ Failed to delete {doc_name.split('/')[-1]}: {e}")
            failed_count += 1
    
    print()
    print("="*80)
    print(f"✅ Deleted {deleted_count} documents")
    if failed_count > 0:
        print(f"❌ Failed {failed_count} documents")
    print("="*80)
    print()
    print("You can now re-index summaries with:")
    print(f"  python services/embedding/index_documents.py --summaries-only --source-id {source_id}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
