"""
Trigger summarization for a specific source_id
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.processing.summarize_chunks import summarize_chunks

if __name__ == "__main__":
    source_id = "youtube_huatdMMekFc_69480fb9"

    print(f"Triggering summarization for: {source_id}")
    print("=" * 70)

    try:
        summary_path = summarize_chunks(source_id)
        print(f"✓ Summary created at: {summary_path}")
        print("=" * 70)
        print("Done! Check your manifest - the source should now be 'ready_for_approval'")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
