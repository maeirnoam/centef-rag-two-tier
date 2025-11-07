# CENTEF RAG - Quick Start Guide

## What Was Created

The `centef-rag-new` project has been scaffolded with the following structure:

```
centef-rag-new/
├── shared/                           # ✅ Core shared modules
│   ├── __init__.py
│   ├── schemas.py                    # Chunk, Summary, JSONL helpers
│   └── manifest.py                   # ManifestEntry, CRUD operations
├── tools/                            # ✅ Processing pipeline
│   ├── __init__.py
│   └── processing/
│       ├── __init__.py
│       ├── process_pdf.py           # PDF → page chunks (PyMuPDF)
│       ├── process_docx.py          # DOCX → section chunks
│       ├── process_image.py         # Image → OCR extraction
│       ├── process_srt.py           # SRT → timestamp chunks
│       └── summarize_chunks.py      # Gemini summarization
├── services/                         # ✅ Embedding pipeline
│   ├── __init__.py
│   └── embedding/
│       ├── __init__.py
│       └── index_documents.py       # Discovery Engine indexing
├── apps/                             # ✅ FastAPI application
│   ├── __init__.py
│   └── agent_api/
│       ├── __init__.py
│       ├── main.py                  # API endpoints
│       ├── retriever_vertex_search.py  # Two-tier search
│       └── synthesizer.py           # Gemini answer generation
├── .env.example                      # ✅ Configuration template
├── .gitignore                        # ✅ Git ignore rules
├── requirements.txt                  # ✅ Python dependencies
├── README.md                         # ✅ Full documentation
└── __init__.py
```

## Next Steps

### 1. Configure Environment

```powershell
# Copy environment template
Copy-Item .env.example .env

# Edit .env and fill in:
# - PROJECT_ID=sylvan-faculty-476113-c9
# - VERTEX_SEARCH_LOCATION=global
# - GENERATION_LOCATION=us-central1
# - All datastore IDs and bucket names from your deployment
```

### 2. Install Dependencies

```powershell
cd centef-rag-new
pip install -r requirements.txt
```

### 3. Set Up Google Cloud Authentication

```powershell
# Option 1: User credentials
gcloud auth application-default login

# Option 2: Service account
$env:GOOGLE_APPLICATION_CREDENTIALS="path\to\service-account.json"
```

### 4. Test the API

```powershell
# Start the server
python apps/agent_api/main.py

# In another terminal, test:
curl http://localhost:8000/health
```

## What's Implemented (with TODOs)

### ✅ Fully Structured
- Manifest lifecycle management (CRUD operations)
- Chunk and Summary schemas with proper dataclasses
- FastAPI endpoints for manifest management
- Proper module structure with imports
- **PyMuPDF PDF processing** with page-level extraction
- **DOCX processing** with section-based chunking
- **Image OCR** with Vision API or Tesseract support
- **GCS path handling** throughout all modules

### ⚠️ Needs Integration (marked with TODO)
1. **Gemini API**: Add Vertex AI calls in `summarize_chunks.py` and `synthesizer.py`
2. **Discovery Engine**: Implement document import in `index_documents.py`
3. **Vertex Search**: Implement actual search in `retriever_vertex_search.py`

## Key Features

### Manifest-Driven Workflow
All operations check and update the central manifest:
- `GET /manifest` - List documents with optional status filter
- `PUT /manifest/{source_id}` - Update document (auto-triggers embedding)

### Status Pipeline
```
pending_processing → pending_summary → pending_approval → pending_embedding → embedded
```

### Two-Tier Search
- Summary datastore: Document-level overviews
- Chunk datastore: Granular content with anchors (page/timestamp)

### Type-Safe Schemas
- `Chunk`: File metadata + anchor (page/timestamp) + content
- `Summary`: Summary text + extracted metadata
- `ManifestEntry`: Full document lifecycle tracking

## Testing Individual Components

```powershell
# Test PDF processing (PyMuPDF)
python tools/processing/process_pdf.py --source-id "test-123" --input "test.pdf"

# Test DOCX processing
python tools/processing/process_docx.py --source-id "test-456" --input "test.docx"

# Test image OCR
python tools/processing/process_image.py --source-id "test-789" --input "test.png"

# Test summarization
python tools/processing/summarize_chunks.py --source-id "test-123"

# Test indexing
python services/embedding/index_documents.py --source-id "test-123"
```

## Integration Points

1. **Frontend**: Calls `POST /manifest` to create entries, `PUT /manifest/{id}` to approve
2. **Processing**: Scripts update manifest status as they complete
3. **Embedding**: Triggered automatically when status → `pending_embedding`
4. **Search**: (TODO) Implement in `/search` endpoint

## Documentation

See `README.md` for full documentation including:
- Architecture overview
- API reference
- Development guidelines
- Manifest schema
- Document lifecycle

## Support

All core functionality has clear TODO comments indicating where to integrate:
- Google Cloud Storage operations
- Vertex AI Gemini calls
- Discovery Engine API calls

Follow the established patterns in each module for consistency.
