"""
End-to-end pipeline: Process all files from local folder to indexed datastores.

Steps:
1. Scan local folder for PDF/DOCX files
2. Match files to manifest entries by filename
3. Process each file (PDF/DOCX) to extract chunks
4. Summarize chunks with Gemini
5. Upload to GCS
6. Index to Discovery Engine (chunks + summaries)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import get_manifest_entries, update_manifest_entry, get_manifest_entry
from tools.processing.process_pdf import process_pdf_to_chunks
from tools.processing.process_docx import process_docx_to_chunks
from tools.processing.summarize_chunks import summarize_chunks_to_summary
from services.embedding.index_documents import index_document

# Configuration
LOCAL_FOLDER = r"C:\Users\User\PycharmProjects\centef-rag-fresh\data\CTF - Essential Readings"

print("="*80)
print("END-TO-END PROCESSING PIPELINE")
print("="*80)
print(f"\nSource folder: {LOCAL_FOLDER}")
print()

# Step 1: Scan folder for files
print("[1/6] Scanning local folder...")
local_files = []
for ext in ['*.pdf', '*.docx']:
    local_files.extend(list(Path(LOCAL_FOLDER).glob(ext)))

print(f"Found {len(local_files)} files:")
for f in local_files:
    print(f"  - {f.name}")

# Step 2: Load manifest and match files
print(f"\n[2/6] Matching files to manifest entries...")
manifest_entries = get_manifest_entries()
matched = []

for local_file in local_files:
    # Find matching manifest entry by filename
    entry = None
    for e in manifest_entries:
        if e.filename == local_file.name:
            entry = e
            break
    
    if entry:
        matched.append({
            'local_path': str(local_file),
            'entry': entry,
            'filename': local_file.name
        })
        print(f"  ✅ {local_file.name} -> {entry.source_id}")
    else:
        print(f"  ⚠️  {local_file.name} -> No manifest entry found (skipping)")

print(f"\nMatched {len(matched)} files to process")

if not matched:
    print("\n❌ No files to process. Exiting.")
    sys.exit(0)

# Ask confirmation
proceed = input(f"\n✅ Process all {len(matched)} files? (yes/no): ").strip().lower()
if proceed not in ['yes', 'y']:
    print("Cancelled.")
    sys.exit(0)

print()

# Process each file
for i, item in enumerate(matched, 1):
    local_path = item['local_path']
    entry = item['entry']
    filename = item['filename']
    
    print("="*80)
    print(f"[{i}/{len(matched)}] Processing: {filename}")
    print("="*80)
    
    try:
        # Step 3: Extract chunks based on file type
        print(f"\n[3/6] Extracting chunks from {filename}...")
        
        if filename.lower().endswith('.pdf'):
            chunks = process_pdf_to_chunks(
                pdf_path=local_path,
                source_id=entry.source_id,
                metadata=entry.metadata
            )
        elif filename.lower().endswith('.docx'):
            chunks = process_docx_to_chunks(
                docx_path=local_path,
                source_id=entry.source_id,
                metadata=entry.metadata
            )
        else:
            print(f"  ⚠️  Unsupported file type, skipping")
            continue
        
        print(f"  ✅ Extracted {len(chunks)} chunks")
        
        # Step 4: Summarize chunks
        print(f"\n[4/6] Summarizing chunks with Gemini...")
        summary = summarize_chunks_to_summary(
            chunks=chunks,
            source_id=entry.source_id,
            filename=filename,
            metadata=entry.metadata
        )
        print(f"  ✅ Generated summary ({len(summary.summary_text)} chars)")
        
        # Step 5: Upload to GCS happens automatically in the processing functions
        print(f"\n[5/6] Files uploaded to GCS")
        print(f"  Chunks: {entry.data_path}")
        print(f"  Summary: {entry.summary_path}")
        
        # Step 6: Update manifest status to trigger indexing
        print(f"\n[6/6] Updating manifest and indexing to Discovery Engine...")
        update_manifest_entry(entry.source_id, {'status': 'pending_embedding'})
        
        # Refresh entry
        entry = get_manifest_entry(entry.source_id)
        
        # Index to datastores
        result = index_document(entry)
        
        if result['success']:
            chunks_success = result.get('chunks', {}).get('success', 0)
            chunks_total = result.get('chunks', {}).get('total', 0)
            summary_success = result.get('summary', {}).get('success', False)
            
            print(f"\n✅ SUCCESS")
            print(f"  Chunks indexed: {chunks_success}/{chunks_total}")
            print(f"  Summary indexed: {'Yes' if summary_success else 'No'}")
        else:
            print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}")
        
        print()
        
    except Exception as e:
        print(f"\n❌ ERROR processing {filename}: {e}")
        import traceback
        traceback.print_exc()
        continue

print()
print("="*80)
print("PIPELINE COMPLETE")
print("="*80)
print(f"\nProcessed {len(matched)} documents")
print("\nYou can now test search with:")
print("  python quick_test.py")
