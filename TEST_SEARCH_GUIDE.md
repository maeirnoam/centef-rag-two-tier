# Testing Two-Tier Search Retrieval

This guide explains how to test the Vertex AI Search integration for the CENTEF RAG system.

## Setup

### 1. Ensure Environment Variables are Set

Create a `.env` file in the `centef-rag-two-tier` directory with your actual values:

```bash
PROJECT_ID=sylvan-faculty-476113-c9
VERTEX_SEARCH_LOCATION=global
GENERATION_LOCATION=us-central1

CHUNKS_DATASTORE_ID=centef-chunk-data-store_1761831236752_gcs_store
SUMMARIES_DATASTORE_ID=centef-summaries-datastore_1762162632284_gcs_store

SOURCE_BUCKET=centef-rag-bucket
TARGET_BUCKET=centef-rag-chunks
MANIFEST_PATH=gs://centef-rag-bucket/manifest/manifest.jsonl

SUMMARY_MODEL=gemini-2.5-flash
```

### 2. Install Dependencies

Make sure you have the required packages installed:

```powershell
pip install -r requirements.txt
```

This includes:
- `google-cloud-discoveryengine` - For Vertex AI Search
- `python-dotenv` - For environment variable management
- `fastapi` and `uvicorn` - For the API server

### 3. Authenticate with Google Cloud

```powershell
gcloud auth application-default login
```

Or set a service account key:

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="path\to\service-account-key.json"
```

## Running Tests

### Option 1: Interactive Test Script

Run the test script to verify search functionality:

```powershell
cd centef-rag-two-tier
python test_search.py
```

The script will:
1. Check environment configuration
2. Prompt for a search query (or use default: "climate change")
3. Test chunk search
4. Test summary search
5. Test combined two-tier search
6. Optionally test retrieving by source_id

### Option 2: Python REPL

Test individual functions directly:

```powershell
cd centef-rag-two-tier
python
```

```python
from dotenv import load_dotenv
load_dotenv()

from apps.agent_api.retriever_vertex_search import search_chunks, search_summaries, search_two_tier

# Test chunk search
chunks = search_chunks("climate change", max_results=5)
print(f"Found {len(chunks)} chunks")
for chunk in chunks:
    print(f"- {chunk['title']}: {chunk['content'][:100]}...")

# Test summary search
summaries = search_summaries("climate change", max_results=3)
print(f"Found {len(summaries)} summaries")
for summary in summaries:
    print(f"- {summary['title']}: {summary['summary_text'][:100]}...")

# Test two-tier search
results = search_two_tier("climate change")
print(f"Summaries: {results['total_summaries']}, Chunks: {results['total_chunks']}")
```

## Understanding the Results

### Chunk Results

Each chunk result contains:
- `id`: Document ID in the datastore
- `content`: The actual text content of the chunk
- `page`: Page number (for PDFs) or `None`
- `start_sec`/`end_sec`: Timestamps (for videos/audio) or `None`
- `source_id`: Original document identifier
- `filename`: Source filename
- `title`: Document title
- `score`: Relevance score from Vertex AI Search
- `metadata`: Additional metadata fields

### Summary Results

Each summary result contains:
- `id`: Document ID in the datastore
- `summary_text`: The document summary
- `source_id`: Original document identifier
- `filename`: Source filename
- `title`: Document title
- `author`: Document author (if available)
- `organization`: Organization (if available)
- `date`: Publication date (if available)
- `publisher`: Publisher (if available)
- `tags`: Topic tags extracted during summarization
- `score`: Relevance score from Vertex AI Search
- `metadata`: Additional metadata fields

### Two-Tier Search

The `search_two_tier()` function combines both searches and returns:
- `query`: The search query
- `summaries`: List of summary results
- `chunks`: List of chunk results
- `total_summaries`: Count of summary results
- `total_chunks`: Count of chunk results

## Filtering by Source ID

To retrieve all content for a specific document:

```python
from apps.agent_api.retriever_vertex_search import retrieve_by_source_id

# Replace with an actual source_id from your datastore
results = retrieve_by_source_id("your-source-id-here")

print(f"Found {results['total_chunks']} chunks")
if results['summary']:
    print(f"Summary: {results['summary']['summary_text']}")
```

## Troubleshooting

### "Import could not be resolved" errors

These are lint warnings that can be ignored if the packages are installed. The code will run correctly.

### Authentication errors

If you see authentication errors:
1. Run `gcloud auth application-default login`
2. Or set `GOOGLE_APPLICATION_CREDENTIALS` to your service account key path

### "Datastore not found" errors

Verify your datastore IDs are correct:
```powershell
gcloud discovery-engine data-stores list --location=global --collection=default_collection --project=sylvan-faculty-476113-c9
```

### No results returned

If searches return no results:
1. Check that documents have been indexed (see manifest with `status=ready`)
2. Try a broader search query
3. Check the datastore in the GCP Console for indexed documents

## Next Steps

Once search is working:
1. Implement answer synthesis with Gemini (see `synthesizer.py`)
2. Create API endpoints to expose search functionality
3. Test end-to-end query → retrieval → synthesis → answer flow
