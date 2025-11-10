# CENTEF RAG System

A production-ready two-tier RAG (Retrieval-Augmented Generation) system using Google Cloud Vertex AI Search and Gemini for terrorism financing research.

## Overview

The CENTEF RAG system provides end-to-end document processing, indexing, and intelligent question-answering:

1. **Processing Pipeline**: Converts documents (PDF, DOCX) into structured chunks with AI-generated summaries
2. **Indexing Pipeline**: Indexes to Vertex AI Search with two-tier datastores (summaries + chunks)
3. **Search & Synthesis**: Two-tier retrieval with Gemini-powered answer generation

All document metadata is tracked in a central `manifest.jsonl` stored in GCS.

## 🚀 Quick Start

### Local Development
```powershell
cd centef-rag-two-tier
.\start_local.ps1
```
See **[QUICK_START_FRONTEND.md](QUICK_START_FRONTEND.md)** for detailed local setup.

### Production Deployment (Google Cloud Run)
```powershell
$env:PROJECT_ID = "your-project-id"
.\deploy-backend.ps1
.\deploy-frontend.ps1
```
See **[CLOUD_RUN_DEPLOYMENT.md](CLOUD_RUN_DEPLOYMENT.md)** for complete deployment guide.

## 📚 Documentation

### Deployment & Setup
- **[CLOUD_RUN_DEPLOYMENT.md](CLOUD_RUN_DEPLOYMENT.md)** - Deploy to Google Cloud Run (Production)
- **[CLOUD_RUN_QUICK_REF.md](CLOUD_RUN_QUICK_REF.md)** - Quick reference for Cloud Run commands
- **[DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)** - Overview of deployment architecture
- **[QUICK_START_FRONTEND.md](QUICK_START_FRONTEND.md)** - Local development setup
- **[QUICK_START.md](QUICK_START.md)** - Backend and pipeline setup

### User & Admin Guides
- **[ADMIN_GUIDE.md](ADMIN_GUIDE.md)** - Admin features and document approval workflow
- **[USER_MANAGEMENT_GUIDE.md](USER_MANAGEMENT_GUIDE.md)** - User administration
- **[CHAT_HISTORY.md](CHAT_HISTORY.md)** - Chat feature documentation

### Developer Documentation
- **[WORKFLOW_OVERVIEW.md](../WORKFLOW_OVERVIEW.md)** - System architecture and data flow
- **[COPILOT_SETUP.md](../COPILOT_SETUP.md)** - AI coding agent instructions

## Key Features

ג… **Multi-Format Processing**: PDF (PyMuPDF) and DOCX with page/section-level chunking
ג… **AI Summarization**: Gemini-powered document summaries with metadata extraction
ג… **Two-Tier Search**: High-level summaries + detailed chunks for optimal retrieval
ג… **Answer Synthesis**: Gemini generates comprehensive answers with citations
ג… **Production Ready**: Complete error handling, logging, and manifest tracking
ג… **Vertex AI Search**: Direct API integration (CreateDocument) for unstructured datastores

## System Architecture

```
centef-rag-two-tier/
ג”ג”€ג”€ shared/                    # Core data structures
ג”‚   ג”ג”€ג”€ schemas.py            # Chunk, Summary, metadata conversion
ג”‚   ג””ג”€ג”€ manifest.py           # Document lifecycle tracking
ג”ג”€ג”€ tools/processing/          # Document processing
ג”‚   ג”ג”€ג”€ process_pdf.py        # PDF ג†’ page chunks (PyMuPDF)
ג”‚   ג”ג”€ג”€ process_docx.py       # DOCX ג†’ section chunks
ג”‚   ג””ג”€ג”€ summarize_chunks.py   # Gemini summarization
ג”ג”€ג”€ services/embedding/        # Indexing service
ג”‚   ג””ג”€ג”€ index_documents.py    # Index to Vertex AI Search
ג”ג”€ג”€ apps/agent_api/           # Query interface
ג”‚   ג”ג”€ג”€ retriever_vertex_search.py  # Two-tier search
ג”‚   ג””ג”€ג”€ synthesizer.py        # Answer generation with Gemini
ג”ג”€ג”€ Helper Scripts:
ג”‚   ג”ג”€ג”€ process_and_index_all.py   # End-to-end pipeline
ג”‚   ג”ג”€ג”€ test_rag_pipeline.py       # Test search + synthesis
ג”‚   ג”ג”€ג”€ quick_test.py              # Test search only
ג”‚   ג”ג”€ג”€ purge_datastores.py        # Clear all indexed data
ג”‚   ג””ג”€ג”€ list_chunks.py / list_summaries.py  # Inspect datastores
ג””ג”€ג”€ requirements.txt          # Python dependencies
```

## Setup

### 1. Prerequisites

- Python 3.10+
- Google Cloud Project with:
  - Cloud Storage buckets: `centef-rag-bucket` (sources/manifest), `centef-rag-chunks` (data/summaries)
  - Vertex AI Search app with two datastores:
    - Chunks datastore: `centef-chunk-data-store_*_gcs_store`
    - Summaries datastore: `centef-summaries-datastore_*_gcs_store`
  - Vertex AI API enabled (for Gemini)
  - Discovery Engine API enabled

### 2. Environment Configuration

Copy the example environment file and fill in your values:

```powershell
Copy-Item .env.example .env
```

Edit `.env` with your GCP project details:
- `PROJECT_ID`: Your Google Cloud project ID (e.g., `sylvan-faculty-476113-c9`)
- `VERTEX_SEARCH_LOCATION`: Region for search (usually `global`)
- `GENERATION_LOCATION`: Region for Gemini (e.g., `us-central1`)
- `SUMMARY_MODEL`: Gemini model for summarization (e.g., `gemini-2.5-flash`)
- Bucket names and datastore IDs from your actual deployment
- `CHUNKS_DATASTORE_ID`: Full datastore ID including `_gcs_store` suffix
- `SUMMARIES_DATASTORE_ID`: Full datastore ID including `_gcs_store` suffix

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Google Cloud Authentication

Set up authentication:

```powershell
gcloud auth application-default login
```

Or use a service account:

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="path\to\service-account-key.json"
```

## Usage

### Quick Start: Process All Documents from Local Folder

The easiest way to process and index documents:

```powershell
python process_and_index_all.py
```

This script will:
1. Find all PDF and DOCX files in `local_docs/`
2. Process each file (extract text ג†’ create chunks)
3. Generate Gemini summaries with metadata
4. Index chunks and summaries to Vertex AI Search

### Test the RAG System

Run a complete end-to-end test with search and answer generation:

```powershell
python test_rag_pipeline.py
```

Example queries:
- "what is AML?"
- "what recent events took place by CENTEF?"

For search-only testing without answer generation:

```powershell
python quick_test.py
```

### Manual Document Processing

#### Step 1: Upload Document to GCS

```powershell
gsutil cp document.pdf gs://centef-rag-bucket/sources/
```

#### Step 2: Create Manifest Entry

```powershell
python -c "from shared.manifest import ManifestEntry, create_manifest_entry; entry = ManifestEntry(source_id='doc-2025-001', filename='document.pdf', title='Document Title', mimetype='application/pdf', source_uri='gs://centef-rag-bucket/sources/document.pdf'); create_manifest_entry(entry)"
```

#### Step 3: Process Document

For PDF:
```powershell
python tools/processing/process_pdf.py --source-id "doc-2025-001" --input "gs://centef-rag-bucket/sources/document.pdf"
```

For DOCX:
```powershell
python tools/processing/process_docx.py --source-id "doc-2025-002" --input "document.docx"
```

#### Step 4: Generate Summary

```powershell
python tools/processing/summarize_chunks.py --source-id "doc-2025-001"
```

#### Step 5: Approve and Index

```powershell
# Mark as approved
python -c "from shared.manifest import update_manifest_entry; update_manifest_entry('doc-2025-001', {'approved': True, 'status': 'pending_embedding'})"

# Index to Vertex AI Search
python services/embedding/index_documents.py --source-id "doc-2025-001"
```

### Datastore Management

#### List Indexed Documents

```powershell
# List all chunks
python list_chunks.py

# List all summaries
python list_summaries.py
```

#### Delete Specific Documents

```powershell
# Delete chunks for a document
python delete_chunks.py doc-2025-001

# Delete summary for a document
python delete_summary.py doc-2025-001
```

#### Purge All Indexed Data

```powershell
python purge_datastores.py
```

**Warning**: This will delete ALL documents from both datastores!

### Running the API (Coming Soon)

Start the FastAPI server:

```powershell
python apps/agent_api/main.py
```

Or with uvicorn:

```powershell
uvicorn apps.agent_api.main:app --reload --port 8080
```

API will be available at `http://localhost:8080`

**Note**: The `/search` endpoint is currently being developed. Use `test_rag_pipeline.py` for testing the complete RAG functionality.

## Document Lifecycle

Each document flows through these statuses:

1. `pending_processing` ג†’ Document uploaded, needs chunking
2. `pending_summary` ג†’ Chunks created, needs summary
3. `pending_approval` ג†’ Summary ready, awaiting human review
4. `pending_embedding` ג†’ Approved, ready to index
5. `embedded` ג†’ Indexed and searchable
6. `error` ג†’ Processing failed

## Manifest Structure

Each document in `gs://centef-rag-bucket/manifest/manifest.jsonl`:

```json
{
  "source_id": "unique-id",
  "filename": "document.pdf",
  "title": "Document Title",
  "mimetype": "application/pdf",
  "source_uri": "gs://centef-rag-bucket/sources/...",
  "status": "embedded",
  "approved": true,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z",
  "ingested_by": "frontend",
  "notes": "",
  "author": "John Doe",
  "organization": "CENTEF",
  "date": "2025-01-01",
  "publisher": "Publisher Name",
  "tags": ["topic1", "topic2"],
  "data_path": "gs://centef-chunk-bucket/data/unique-id.jsonl",
  "summary_path": "gs://centef-chunk-bucket/summaries/unique-id.jsonl"
}
```

## Development

### Adding New Document Types

1. Create a new processor in `tools/processing/` (e.g., `process_docx.py`)
2. Follow the pattern from `process_pdf.py`:
   - Read manifest entry
   - Extract and chunk content
   - Create `Chunk` objects with appropriate `ChunkAnchor`
   - Write to GCS
   - Update manifest status

### Extending the API

Add new endpoints in `apps/agent_api/main.py`. Use the shared manifest helpers for consistency.

## Implemented Features

### Document Processing
ג… **PyMuPDF PDF Processing**: Full text extraction with page-level chunking
ג… **DOCX Processing**: Section-based chunking with heading detection  
ג… **Image OCR**: Supports both Google Cloud Vision API and Tesseract
ג… **SRT Processing**: Timestamp-based chunking for subtitles
ג… **GCS Integration**: All processors handle GCS paths correctly
ג… **Gemini Summarization**: Automatic summary generation with metadata extraction

### Indexing & Search
ג… **Vertex AI Discovery Engine**: Full integration with CreateDocument API
ג… **Two-Tier Search**: Retrieves both summaries and chunks for comprehensive context
ג… **Batch Indexing**: Process multiple documents from local folder
ג… **Datastore Management**: Purge, list, and delete indexed documents

### Answer Generation
ג… **Gemini Synthesis**: Full answer generation using gemini-2.0-flash-exp
ג… **Domain Context**: Built-in knowledge (AML=Anti-Money Laundering, CTF=Counter-Terrorism Financing)
ג… **Citations**: Automatic source attribution with document titles and page numbers
ג… **Prompt Engineering**: Comprehensive prompts with retrieved context

### Helper Tools
ג… **process_and_index_all.py**: End-to-end pipeline from local files to indexed datastores
ג… **test_rag_pipeline.py**: Complete RAG testing with search + synthesis
ג… **quick_test.py**: Search-only testing for debugging
ג… **purge_datastores.py**: Clear all documents from both datastores
ג… **list_chunks.py / list_summaries.py**: Inspect datastore contents
ג… **delete_chunks.py / delete_summary.py**: Selective document deletion

## Tested Queries

The system has been validated with real-world queries:
- "what is AML?" ג†’ Retrieved 2 summaries + 5 chunks, generated comprehensive definition with examples
- "what recent events took place by CENTEF?" ג†’ Retrieved 1 summary + 5 chunks, detailed Jan 8, 2025 Syria panel information

## TODO

Future enhancements:
1. **FastAPI Endpoints**: Add RESTful search endpoint to expose RAG functionality
2. **Additional Processors**: PPTX, audio, video, YouTube processors
3. **Follow-up Questions**: Generate related questions based on user queries
4. **Multi-turn Conversations**: Maintain conversation history for context
5. **Enhanced Filtering**: Search by date range, author, organization, tags

## References

- [Vertex AI Search Documentation](https://cloud.google.com/generative-ai-app-builder/docs)
- [Vertex AI Gemini Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## License

[Your License Here]


