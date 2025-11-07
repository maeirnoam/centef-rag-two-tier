"""
Test script for processing a PDF file through the CENTEF RAG pipeline.
This will create a manifest entry, process the PDF, generate summary, and index.
"""
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import ManifestEntry, create_manifest_entry, DocumentStatus
from tools.processing.process_pdf import process_pdf
from tools.processing.summarize_chunks import summarize_chunks
from services.embedding.index_documents import index_document

# Load environment
from dotenv import load_dotenv
load_dotenv()

def clean_filename(original_filename: str) -> str:
    """Clean filename by removing special characters and spaces."""
    # Remove or replace problematic characters
    cleaned = original_filename.replace(" ", "_")
    cleaned = cleaned.replace(":", "")
    cleaned = cleaned.replace("'", "")
    cleaned = cleaned.replace('"', '')
    return cleaned

def test_pdf_pipeline(pdf_path: str, original_filename: str):
    """
    Run complete PDF processing pipeline.
    
    Args:
        pdf_path: Path to PDF file (local or gs://)
        original_filename: Original filename for the document
    """
    print("\n" + "="*80)
    print("CENTEF RAG - PDF Processing Test")
    print("="*80 + "\n")
    
    # Generate source_id and clean filename
    source_id = str(uuid.uuid4())
    clean_name = clean_filename(original_filename)
    
    print(f"📄 Original filename: {original_filename}")
    print(f"📝 Clean filename: {clean_name}")
    print(f"🆔 Source ID: {source_id}\n")
    
    # Step 1: Create manifest entry
    print("Step 1: Creating manifest entry...")
    try:
        entry = ManifestEntry(
            source_id=source_id,
            filename=clean_name,
            title=clean_name.replace(".pdf", "").replace("_", " "),
            mimetype="application/pdf",
            source_uri=pdf_path if pdf_path.startswith("gs://") else f"gs://centef-rag-bucket/sources/{source_id}/{clean_name}",
            status=DocumentStatus.PENDING_PROCESSING,
            ingested_by="test_script"
        )
        
        created_entry = create_manifest_entry(entry)
        print(f"✓ Manifest entry created with status: {created_entry.status}\n")
    except Exception as e:
        print(f"✗ Error creating manifest entry: {e}")
        return
    
    # Step 2: Process PDF
    print("Step 2: Processing PDF (extracting text, creating chunks)...")
    try:
        data_path = process_pdf(source_id, pdf_path)
        print(f"✓ PDF processed successfully")
        print(f"  Chunks saved to: {data_path}\n")
    except Exception as e:
        print(f"✗ Error processing PDF: {e}")
        return
    
    # Step 3: Generate summary
    print("Step 3: Generating summary with Gemini...")
    try:
        summary_path = summarize_chunks(source_id)
        print(f"✓ Summary generated successfully")
        print(f"  Summary saved to: {summary_path}\n")
    except Exception as e:
        print(f"✗ Error generating summary: {e}")
        return
    
    # Step 4: Wait for manual approval
    print("Step 4: Manual approval (setting to pending_embedding)...")
    from shared.manifest import update_manifest_entry
    try:
        updated_entry = update_manifest_entry(source_id, {
            "status": DocumentStatus.PENDING_EMBEDDING,
            "approved": True
        })
        print(f"✓ Status updated to: {updated_entry.status}\n")
    except Exception as e:
        print(f"✗ Error updating manifest: {e}")
        return
    
    # Step 5: Index to Discovery Engine
    print("Step 5: Indexing to Vertex AI Search...")
    try:
        index_document(updated_entry)
        print(f"✓ Document indexed successfully\n")
    except Exception as e:
        print(f"✗ Error indexing document: {e}")
        return
    
    print("="*80)
    print("✓ COMPLETE! PDF processed through entire pipeline")
    print("="*80)
    print(f"\nSource ID: {source_id}")
    print(f"Status: embedded")
    print(f"\nYou can now search for this document in your Vertex AI Search app!")
    print("="*80 + "\n")


if __name__ == "__main__":
    # Configuration
    ORIGINAL_FILENAME = "Commentary_ The Dangers of Overreliance on Generative AI in the CT Fight.pdf"
    
    # You can set this to either:
    # 1. Local path: r"C:\path\to\downloaded\file.pdf"
    # 2. GCS path: "gs://centef-rag-bucket/sources/folder/file.pdf"
    
    # For now, let's assume you'll upload to GCS first
    PDF_PATH = "gs://centef-rag-bucket/sources/Commentary_The_Dangers_of_Overreliance_on_Generative_AI_in_the_CT_Fight.pdf"
    
    print("\nBefore running this script, make sure to:")
    print("1. Download the PDF from Google Drive")
    print("2. Upload it to GCS using:")
    print(f"   gsutil cp \"<local_path>\" {PDF_PATH}")
    print("\nOr provide a local path and the script will handle it.\n")
    
    response = input("Have you uploaded the PDF to GCS? (y/n): ")
    
    if response.lower() == 'y':
        test_pdf_pipeline(PDF_PATH, ORIGINAL_FILENAME)
    else:
        print("\nPlease upload the PDF first, then run this script again.")
        print(f"\nCommand to upload:")
        print(f'gsutil cp "C:\\path\\to\\{ORIGINAL_FILENAME}" {PDF_PATH}')
