"""
Simple test to verify description field works in ManifestEntry
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import ManifestEntry, DocumentStatus
import json

def test_description_field():
    """Test that description is properly handled in ManifestEntry"""

    test_description = "This is a test description for the document.\nIt has multiple lines.\nAnd should be preserved."

    print("\n" + "="*60)
    print("Testing Description Field in ManifestEntry")
    print("="*60 + "\n")

    # Create entry with description
    entry = ManifestEntry(
        source_id="test_123",
        filename="test_document.pdf",
        title="Test Document",
        mimetype="application/pdf",
        source_uri="gs://test-bucket/test.pdf",
        ingested_by="test",
        notes="Test notes",
        description=test_description,
        status=DocumentStatus.PENDING_PROCESSING
    )

    print(f"Created ManifestEntry with description:")
    print(f"  Description: {repr(entry.description)}\n")

    # Convert to dict
    entry_dict = entry.to_dict()
    print("Entry as dictionary:")
    print(json.dumps(entry_dict, indent=2))
    print()

    # Verify description is in dict
    if "description" in entry_dict and entry_dict["description"] == test_description:
        print("="*60)
        print("SUCCESS: Description field is included in to_dict()")
        print("="*60 + "\n")
    else:
        print("="*60)
        print("FAILURE: Description not properly serialized")
        print("="*60 + "\n")
        return False

    # Test from_dict
    print("Testing from_dict()...")
    reconstructed_entry = ManifestEntry.from_dict(entry_dict)

    if reconstructed_entry.description == test_description:
        print("="*60)
        print("SUCCESS: Description field is properly deserialized")
        print("="*60 + "\n")
        return True
    else:
        print("="*60)
        print("FAILURE: Description not properly deserialized")
        print(f"  Expected: {repr(test_description)}")
        print(f"  Got: {repr(reconstructed_entry.description)}")
        print("="*60 + "\n")
        return False

if __name__ == "__main__":
    try:
        success = test_description_field()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
