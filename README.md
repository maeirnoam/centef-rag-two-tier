# CENTEF RAG System

A Google Cloud-based multimodal retrieval-augmented generation (RAG) platform for processing, indexing, and searching documents using Vertex AI Search and Gemini.

## Overview

The CENTEF RAG system provides three coordinated pipelines:

1. **Processing Pipeline**: Converts raw sources (PDF, DOCX, PPTX, SRT, audio, video) into structured chunks and summaries
2. **Embedding Pipeline**: Indexes verified documents into Vertex AI Search datastores
3. **Search Pipeline**: Retrieves and synthesizes answers using two-tier search (summaries + chunks)

All document lifecycle and metadata is tracked in a central `manifest.jsonl`.

## Architecture

```
centef-rag-new/
├── shared/                    # Shared schemas and utilities
│   ├── schemas.py            # Chunk and summary dataclasses
│   └── manifest.py           # Manifest management
├── tools/
│   └── processing/           # Document processing tools
│       ├── process_pdf.py    # PDF → page chunks (PyMuPDF)
│       ├── process_docx.py   # DOCX → section chunks
│       ├── process_srt.py    # SRT → timestamp chunks
│       ├── process_image.py  # Image → OCR text extraction
│       └── summarize_chunks.py  # Generate summaries with Gemini
├── services/
│   └── embedding/            # Indexing service
│       └── index_documents.py  # Index to Vertex AI Search
├── apps/
│   └── agent_api/            # FastAPI application
│       ├── main.py           # API endpoints
│       ├── retriever_vertex_search.py  # Search both datastores
│       └── synthesizer.py    # Generate answers with Gemini
├── .env.example              # Environment configuration template
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Setup

### 1. Prerequisites

- Python 3.10+
- Google Cloud Project with:
  - Cloud Storage buckets: `centef-rag-bucket`, `centef-chunk-bucket`
  - Vertex AI Search app with two datastores:
    - `centef-chunk-data-store`
    - `centef-summary-data-store`
  - Vertex AI API enabled (for Gemini)

### 2. Environment Configuration

Copy the example environment file and fill in your values:

```powershell
Copy-Item .env.example .env
```

Edit `.env` with your GCP project details:
- `PROJECT_ID`: Your Google Cloud project ID (e.g., `sylvan-faculty-476113-c9`)
- `VERTEX_SEARCH_LOCATION`: Region for search (usually `global`)
- `GENERATION_LOCATION`: Region for Gemini (e.g., `us-central1`)
- Bucket names and datastore IDs from your actual deployment

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

### Processing Documents

#### Process a PDF (using PyMuPDF)
```powershell
python tools/processing/process_pdf.py --source-id "doc-123" --input "path/to/document.pdf"
```

#### Process a DOCX file
```powershell
python tools/processing/process_docx.py --source-id "doc-456" --input "path/to/document.docx"
```

#### Process an image with OCR
```powershell
python tools/processing/process_image.py --source-id "img-789" --input "path/to/image.png"
```

#### Process an SRT file
```powershell
python tools/processing/process_srt.py --source-id "video-456" --input "path/to/subtitles.srt"
```

#### Generate summary and extract metadata
```powershell
python tools/processing/summarize_chunks.py --source-id "doc-123"
```

### Indexing Documents

After processing and approval, index documents to Vertex AI Search:

```powershell
python services/embedding/index_documents.py --source-id "doc-123"
```

### Running the API

Start the FastAPI server:

```powershell
python apps/agent_api/main.py
```

Or with uvicorn:

```powershell
uvicorn apps.agent_api.main:app --reload --port 8000
```

API will be available at `http://localhost:8000`

### API Endpoints

#### Manifest Management

- `GET /manifest` - List all documents (optional `?status=` filter)
- `GET /manifest/{source_id}` - Get specific document
- `POST /manifest` - Create new document entry
- `PUT /manifest/{source_id}` - Update document (triggers embedding when `status=pending_embedding`)

#### Search (TODO)

- `POST /search` - Search documents and generate answers

## Document Lifecycle

Each document flows through these statuses:

1. `pending_processing` → Document uploaded, needs chunking
2. `pending_summary` → Chunks created, needs summary
3. `pending_approval` → Summary ready, awaiting human review
4. `pending_embedding` → Approved, ready to index
5. `embedded` → Indexed and searchable
6. `error` → Processing failed

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

## TODO

The following features are marked with TODO comments and need implementation:

1. **Gemini Integration**: Replace placeholder prompts with actual Vertex AI Gemini calls in `summarize_chunks.py` and `synthesizer.py`
2. **Discovery Engine**: Implement document import/search using Discovery Engine API in `index_documents.py` and `retriever_vertex_search.py`
3. **Additional Processors**: Add PPTX, audio, video, YouTube processors following the established patterns
4. **Search Endpoint**: Implement full search → retrieval → synthesis pipeline in `main.py`

### Implemented Features

✅ **PyMuPDF PDF Processing**: Full text extraction with page-level chunking
✅ **DOCX Processing**: Section-based chunking with heading detection  
✅ **Image OCR**: Supports both Google Cloud Vision API and Tesseract
✅ **SRT Processing**: Timestamp-based chunking for subtitles
✅ **GCS Integration**: All processors handle GCS paths correctly
✅ **Environment Configuration**: All settings from your actual `.env` file

## References

- [Vertex AI Search Documentation](https://cloud.google.com/generative-ai-app-builder/docs)
- [Vertex AI Gemini Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## License

[Your License Here]
