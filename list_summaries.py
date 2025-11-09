"""List all summary documents in the datastore."""
import os
from dotenv import load_dotenv
from google.cloud import discoveryengine_v1beta as discoveryengine

load_dotenv()

PROJECT_ID = os.getenv('PROJECT_ID')
SUMMARIES_DATASTORE_ID = os.getenv('SUMMARIES_DATASTORE_ID')

client = discoveryengine.DocumentServiceClient()

parent = (
    f"projects/{PROJECT_ID}/"
    f"locations/global/"
    f"collections/default_collection/"
    f"dataStores/{SUMMARIES_DATASTORE_ID}/"
    f"branches/default_branch"
)

print(f"Listing summaries from: {SUMMARIES_DATASTORE_ID}")
print()

request = discoveryengine.ListDocumentsRequest(
    parent=parent,
    page_size=100
)

docs = list(client.list_documents(request=request))

print(f"Found {len(docs)} summaries:")
print()

for doc in docs:
    doc_id = doc.name.split('/')[-1]
    print(f"  {doc_id}")
