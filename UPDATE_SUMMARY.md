# Update Summary - PyMuPDF, DOCX, and Image Processing

## Changes Made

### 1. Updated Environment Configuration ✅

**File: `.env.example`**
- Replaced generic placeholder values with actual configuration from your `.env`
- Updated variable names to match your deployment:
  - `PROJECT_ID` (was `GCP_PROJECT_ID`)
  - `VERTEX_SEARCH_LOCATION` (was `GCP_LOCATION`)
  - `GENERATION_LOCATION` (new)
  - `TARGET_BUCKET` (was `CHUNK_BUCKET`)
  - `SOURCE_BUCKET` (new)
  - `CHUNKS_DATASTORE_ID` (with actual ID)
  - `SUMMARIES_DATASTORE_ID` (with actual ID)
  - `DISCOVERY_SERVING_CONFIG` (new, full path)
  - `MANIFEST_PATH` (full GCS path)

### 2. Updated Dependencies ✅

**File: `requirements.txt`**
- ✅ Added `PyMuPDF==1.23.8` (replaces PyPDF2)
- ✅ Added `Pillow==10.2.0` for image processing
- ✅ Added `pytesseract==0.3.10` for OCR
- ✅ Kept `python-docx==1.1.0` for DOCX processing
- Added note about Tesseract installation

### 3. Updated process_pdf.py ✅

**File: `tools/processing/process_pdf.py`**
- ✅ Replaced placeholder PDF extraction with **PyMuPDF (fitz)**
- ✅ Implemented `extract_pdf_text_by_page()` with actual text extraction
- ✅ Added `download_from_gcs()` helper for GCS file handling
- ✅ Updated environment variables to use `PROJECT_ID` and `TARGET_BUCKET`
- ✅ Properly handles page iteration with PyMuPDF
- ✅ Cleans and validates extracted text

### 4. Created process_docx.py ✅

**File: `tools/processing/process_docx.py` (NEW)**
- ✅ Full DOCX processing using `python-docx` library
- ✅ Section-based chunking with heading detection
- ✅ Groups paragraphs into logical sections
- ✅ Handles both heading-based and paragraph-count-based chunking
- ✅ GCS download support
- ✅ Uses `ChunkAnchor(section=name)` for section references

### 5. Created process_image.py ✅

**File: `tools/processing/process_image.py` (NEW)**
- ✅ Image OCR processing with dual-mode support:
  - **Google Cloud Vision API** (preferred, better accuracy)
  - **Tesseract OCR** (fallback)
- ✅ Automatic selection based on `USE_VISION_API` env var
- ✅ Full text extraction from images (PNG, JPEG, etc.)
- ✅ GCS download support
- ✅ Creates single chunk per image (no anchor needed)

### 6. Updated Environment Variables Throughout ✅

Updated all files to use correct environment variable names:

**Files updated:**
- `shared/manifest.py`
  - Added `_parse_gcs_path()` helper
  - Updated to use `PROJECT_ID`, `SOURCE_BUCKET`, `TARGET_BUCKET`
  - Handle full GCS paths in `MANIFEST_PATH`
  
- `tools/processing/process_srt.py`
  - Updated to `PROJECT_ID` and `TARGET_BUCKET`
  
- `tools/processing/summarize_chunks.py`
  - Updated to `PROJECT_ID`, `GENERATION_LOCATION`, `TARGET_BUCKET`
  
- `services/embedding/index_documents.py`
  - Updated to `PROJECT_ID`, `VERTEX_SEARCH_LOCATION`
  - Uses `CHUNKS_DATASTORE_ID` and `SUMMARIES_DATASTORE_ID`
  
- `apps/agent_api/retriever_vertex_search.py`
  - Updated to `PROJECT_ID`, `VERTEX_SEARCH_LOCATION`
  - Added `DISCOVERY_SERVING_CONFIG` support
  
- `apps/agent_api/synthesizer.py`
  - Updated to `PROJECT_ID`, `GENERATION_LOCATION`

### 7. Enhanced GCS Support ✅

**File: `shared/schemas.py`**
- ✅ Added `download_from_gcs_if_needed()` helper
- ✅ Added `upload_to_gcs_if_needed()` helper
- ✅ Updated to use `PROJECT_ID` and `TARGET_BUCKET`

### 8. Updated Documentation ✅

**File: `README.md`**
- ✅ Added all three new processors to architecture diagram
- ✅ Updated usage examples with DOCX and image processing
- ✅ Updated environment configuration instructions
- ✅ Marked implemented features (PyMuPDF, DOCX, Image OCR)
- ✅ Removed completed TODOs

**File: `QUICK_START.md`**
- ✅ Updated file listing to show all processors
- ✅ Updated environment configuration examples
- ✅ Added testing examples for new processors
- ✅ Updated "Fully Structured" section with new features

## New File Structure

```
centef-rag-new/
├── tools/processing/
│   ├── process_pdf.py       ✅ PyMuPDF implementation
│   ├── process_docx.py      ✅ NEW - Section-based chunking
│   ├── process_image.py     ✅ NEW - OCR with Vision API/Tesseract
│   ├── process_srt.py       ✅ Updated env vars
│   └── summarize_chunks.py  ✅ Updated env vars
```

## How to Use New Processors

### PDF Processing (PyMuPDF)
```powershell
python tools/processing/process_pdf.py --source-id "doc-123" --input "gs://bucket/file.pdf"
```
- Extracts text page by page
- Creates chunks with `page` anchor
- Handles GCS paths automatically

### DOCX Processing
```powershell
python tools/processing/process_docx.py --source-id "doc-456" --input "document.docx"
```
- Detects headings as section boundaries
- Groups paragraphs into logical sections
- Creates chunks with `section` anchor

### Image OCR
```powershell
python tools/processing/process_image.py --source-id "img-789" --input "gs://bucket/image.png"
```
- Tries Google Cloud Vision API first (if `USE_VISION_API=true`)
- Falls back to Tesseract OCR
- Creates single chunk with extracted text
- No anchor (images are standalone)

## Configuration Requirements

### Your .env file should have:
```bash
PROJECT_ID=sylvan-faculty-476113-c9
VERTEX_SEARCH_LOCATION=global
GENERATION_LOCATION=us-central1
SOURCE_BUCKET=centef-rag-bucket
TARGET_BUCKET=centef-rag-chunks
CHUNKS_DATASTORE_ID=centef-chunk-data-store_1761831236752_gcs_store
SUMMARIES_DATASTORE_ID=centef-summaries-datastore_1762162632284_gcs_store
MANIFEST_PATH=gs://centef-rag-bucket/manifest/manifest.jsonl
DISCOVERY_SERVING_CONFIG=projects/51695993895/locations/global/collections/default_collection/engines/centef-two-tier-search-app/servingConfigs/default_config
```

### For Image OCR (optional):
```bash
USE_VISION_API=true  # Use Google Cloud Vision (recommended)
# OR
USE_VISION_API=false  # Use Tesseract (requires local installation)
```

## Next Steps

1. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

2. **For Tesseract OCR (if not using Vision API):**
   - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - Add to PATH or set `pytesseract.pytesseract.tesseract_cmd`

3. **Test the processors:**
   ```powershell
   # Copy your actual .env
   Copy-Item ..\.env .env
   
   # Test each processor
   python tools/processing/process_pdf.py --source-id "test-pdf" --input "test.pdf"
   python tools/processing/process_docx.py --source-id "test-docx" --input "test.docx"
   python tools/processing/process_image.py --source-id "test-img" --input "test.png"
   ```

## Summary

✅ **PDF Processing**: Fully implemented with PyMuPDF
✅ **DOCX Processing**: Complete with section detection
✅ **Image OCR**: Dual-mode (Vision API + Tesseract)
✅ **Environment**: All variables match your actual deployment
✅ **GCS Support**: All processors handle GCS paths
✅ **Documentation**: Updated README and QUICK_START

All processors follow the same pattern:
1. Get manifest entry
2. Download from GCS if needed
3. Extract/chunk content
4. Create Chunk objects with appropriate anchors
5. Upload to GCS
6. Update manifest status to `pending_summary`
