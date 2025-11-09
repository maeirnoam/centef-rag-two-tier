"""
Driver script to process files in a folder: upload/process, summarize, and index.

Steps per document (if manifest entry exists by filename):
 1. Process file (PDF/DOCX) -> creates chunks and uploads to GCS (updates manifest to PENDING_SUMMARY)
 2. Summarize chunks with Gemini -> uploads summary to GCS (updates manifest to PENDING_APPROVAL)
 3. Set manifest status to PENDING_EMBEDDING
 4. Run indexing to create documents in both datastores

Usage: python process_and_index_folder.py "C:\path\to\folder"
"""
import os
import sys
import subprocess
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python process_and_index_folder.py <folder_path>")
    sys.exit(1)

folder = sys.argv[1]

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import get_manifest_entries, get_manifest_entry, update_manifest_entry

# Gather manifest filename->source_id mapping
entries = get_manifest_entries()
filename_map = {e.filename: e.source_id for e in entries}

print(f"Found {len(filename_map)} manifest entries mapping filenames to source_id")

# Walk the folder for files
files = []
for root, dirs, filenames in os.walk(folder):
    for fn in filenames:
        # skip hidden files
        if fn.startswith('.'):
            continue
        files.append(os.path.join(root, fn))

print(f"Found {len(files)} files under {folder}")

# Process each file
for fpath in files:
    fname = os.path.basename(fpath)
    print('\n' + '='*80)
    print(f"Processing file: {fname}")

    # Try to find manifest entry by exact filename
    if fname in filename_map:
        source_id = filename_map[fname]
        print(f"Matched manifest source_id: {source_id}")
    else:
        # Try matching by filename without extension
        name_no_ext = os.path.splitext(fname)[0]
        # Some manifest filenames may be truncated, try contains
        matched = None
        for k, v in filename_map.items():
            if name_no_ext in k or k in name_no_ext or name_no_ext == os.path.splitext(k)[0]:
                matched = v
                break
        if matched:
            source_id = matched
            print(f"Loosely matched manifest source_id: {source_id} (manifest filename: {k})")
        else:
            print(f"No manifest entry found for {fname}, skipping")
            continue

    ext = fname.lower().split('.')[-1]
    try:
        if ext in ['pdf']:
            # Call the process_pdf script
            cmd = [sys.executable, 'tools/processing/process_pdf.py', '--source-id', source_id, '--input', fpath]
            print(f"Running: {' '.join(cmd)}")
            subprocess.check_call(cmd)
        elif ext in ['docx']:
            cmd = [sys.executable, 'tools/processing/process_docx.py', '--source-id', source_id, '--input', fpath]
            print(f"Running: {' '.join(cmd)}")
            subprocess.check_call(cmd)
        else:
            print(f"Unsupported extension '{ext}', skipping processing for {fname}")
            continue

        # Now summarize
        cmd = [sys.executable, 'tools/processing/summarize_chunks.py', '--source-id', source_id]
        print(f"Running summary: {' '.join(cmd)}")
        subprocess.check_call(cmd)

        # Update manifest to pending_embedding so indexer will process
        print(f"Updating manifest {source_id} -> pending_embedding")
        update_manifest_entry(source_id, {'status': 'pending_embedding'})

        # Index document
        cmd = [sys.executable, 'services/embedding/index_documents.py', '--source-id', source_id]
        print(f"Indexing: {' '.join(cmd)}")
        subprocess.check_call(cmd)

        print(f"Finished processing and indexing {source_id}")

    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
    except Exception as e:
        print(f"Error processing {fname}: {e}")

print('\nAll done')
