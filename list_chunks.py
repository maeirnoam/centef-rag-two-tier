"""List chunks in the datastore."""
import os
from dotenv import load_dotenv
from google.cloud import discoveryengine_v1beta as discoveryengine

load_dotenv()

PROJECT_ID = os.getenv('PROJECT_ID')
CHUNKS_DATASTORE_ID = os.getenv('CHUNKS_DATASTORE_ID')

client = discoveryengine.DocumentServiceClient()

parent = (
    f"projects/{PROJECT_ID}/"
    f"locations/global/"
    f"collections/default_collection/"
    f"dataStores/{CHUNKS_DATASTORE_ID}/"
    f"branches/default_branch"
)

print(f"Listing chunks from: {CHUNKS_DATASTORE_ID}")
print()

request = discoveryengine.ListDocumentsRequest(
    parent=parent,
    page_size=100
)

docs = list(client.list_documents(request=request))

print(f"Found {len(docs)} chunks:")
print()

# Group by source_id
from collections import defaultdict
by_source = defaultdict(int)

for doc in docs[:20]:
    doc_id = doc.name.split('/')[-1]
    print(f"  {doc_id}")
    # Try to extract source_id from doc_id
    if '_page_' in doc_id or '_chunk_' in doc_id:
        source_id = doc_id.rsplit('_', 2)[0]
        by_source[source_id] += 1

if len(docs) > 20:
    print(f"  ... and {len(docs) - 20} more")

print()
print("Chunks by source_id:")
for source_id, count in sorted(by_source.items()):
    print(f"  {source_id}: {count} chunks")
