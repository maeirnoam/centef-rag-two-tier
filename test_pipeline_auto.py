"""
Full Pipeline Test - YouTube Video Upload (Auto-run)
Simulates: Upload → External Download → Transcribe → Translate → Chunk → Summarize → Pending Approval
"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import create_manifest_entry, get_manifest_entry, DocumentStatus, ManifestEntry
from apps.agent_api.main import process_youtube_video
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_full_youtube_pipeline():
    """Test complete YouTube upload pipeline"""
    
    print("=" * 80)
    print("FULL PIPELINE TEST - YouTube Video Upload")
    print("=" * 80)
    print()
    
    # Test video - "Me at the zoo" (first YouTube video, 19 seconds)
    youtube_url = "https://www.youtube.com/watch?v=tLMNzsp7yOw"
    source_language = "he-IL"  # Hebrew
    translate_to = "en"        # Translate to English
    
    print(f"YouTube URL: {youtube_url}")
    print(f"Video: Me at the zoo (19 seconds)")
    print(f"Source Language: {source_language}")
    print(f"Translate To: {translate_to if translate_to else 'None'}")
    print()
    
    # Step 1: Create manifest entry
    print("[1/6] Creating manifest entry...")
    source_id = f"test_youtube_pipeline_{int(time.time())}"
    
    entry = ManifestEntry(
        source_id=source_id,
        filename="me_at_the_zoo.mp4",
        title="Me at the zoo - Full Pipeline Test",
        mimetype="video/youtube",
        source_uri=youtube_url,
        ingested_by="test@example.com",
        notes=f"Full pipeline test: {youtube_url}",
        status=DocumentStatus.PENDING_PROCESSING
    )
    
    created_entry = create_manifest_entry(entry)
    print(f"✓ Manifest entry created: {source_id}")
    print(f"  Status: {created_entry.status}")
    print()
    
    # Step 2-6: Process YouTube video (runs full pipeline)
    print("[2/6] Downloading from external service...")
    print("[3/6] Transcribing audio (Speech-to-Text)...")
    print("[4/6] Translating (if needed)...")
    print("[5/6] Chunking into 30s windows...")
    print("[6/6] Summarizing with Gemini...")
    print()
    print("Starting background processing...")
    print("Expected time: ~2-3 minutes for 19 second video...")
    print()
    
    try:
        # Run the full pipeline
        process_youtube_video(
            source_id=source_id,
            url=youtube_url,
            language=source_language,
            translate=translate_to if translate_to != source_language else None
        )
        
        # Check final status
        print()
        print("=" * 80)
        print("PIPELINE COMPLETED")
        print("=" * 80)
        print()
        
        final_entry = get_manifest_entry(source_id)
        if final_entry:
            print(f"Source ID: {source_id}")
            print(f"Status: {final_entry.status}")
            print(f"Title: {final_entry.title}")
            print(f"Data Path: {final_entry.data_path}")
            print()
            
            if final_entry.status == DocumentStatus.PENDING_APPROVAL:
                print("✓ SUCCESS! Video is ready for admin approval")
                print()
                print("Next steps:")
                print("  1. Open frontend: http://localhost:8080")
                print("  2. Go to Manifest page")
                print(f"  3. Find entry: {source_id}")
                print("  4. Review summary and metadata")
                print("  5. Approve for embedding")
                return True
            else:
                print(f"⚠ Pipeline stopped at status: {final_entry.status}")
                if final_entry.notes:
                    print(f"Notes: {final_entry.notes}")
                return False
        else:
            print("❌ Could not retrieve final manifest entry")
            return False
            
    except Exception as e:
        print()
        print("=" * 80)
        print("PIPELINE FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        
        # Check manifest for error details
        error_entry = get_manifest_entry(source_id)
        if error_entry and error_entry.notes:
            print(f"Error details: {error_entry.notes}")
        
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()
    print("Starting full pipeline test (auto-run)...")
    print()
    
    success = test_full_youtube_pipeline()
    
    print()
    if success:
        print("=" * 80)
        print("✓ FULL PIPELINE TEST PASSED")
        print("=" * 80)
        sys.exit(0)
    else:
        print("=" * 80)
        print("❌ FULL PIPELINE TEST FAILED")
        print("=" * 80)
        sys.exit(1)
