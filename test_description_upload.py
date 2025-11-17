"""
Test script to verify description field is being saved correctly in manifest
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import ManifestEntry, create_manifest_entry, get_manifest_entry, DocumentStatus
import uuid

def test_description_upload():
    """Test that description is saved correctly to manifest"""

    # Create a test manifest entry with a description
    test_source_id = f"test_description_{uuid.uuid4().hex[:8]}"
    test_description = "This is a test description for the document.\nIt has multiple lines.\nAnd should be preserved."

    print(f"\n{'='*60}")
    print("Testing Description Field in Manifest")
    print(f"{'='*60}\n")

    print(f"Creating test entry with source_id: {test_source_id}")
    print(f"Description: {repr(test_description)}\n")

    # Create entry
    entry = ManifestEntry(
        source_id=test_source_id,
        filename="test_document.pdf",
        title="Test Document with Description",
        mimetype="application/pdf",
        source_uri="gs://test-bucket/test_document.pdf",
        ingested_by="test_script",
        notes="Test upload to verify description field",
        description=test_description,
        status=DocumentStatus.PENDING_PROCESSING
    )

    # Save to manifest
    print("Saving entry to manifest...")
    created_entry = create_manifest_entry(entry)
    print(f"✓ Entry created successfully\n")

    # Retrieve and verify
    print("Retrieving entry from manifest...")
    retrieved_entry = get_manifest_entry(test_source_id)

    if not retrieved_entry:
        print("✗ ERROR: Could not retrieve entry from manifest")
        return False

    print(f"✓ Entry retrieved successfully\n")

    # Check description
    print("Verifying description field:")
    print(f"  Expected: {repr(test_description)}")
    print(f"  Actual:   {repr(retrieved_entry.description)}")

    if retrieved_entry.description == test_description:
        print(f"\n{'='*60}")
        print("✓ SUCCESS: Description field is working correctly!")
        print(f"{'='*60}\n")

        # Show the entry as dict
        print("Entry as dictionary:")
        entry_dict = retrieved_entry.to_dict()
        for key, value in entry_dict.items():
            if key == 'description':
                print(f"  {key}: {repr(value)}")

        return True
    else:
        print(f"\n{'='*60}")
        print("✗ FAILURE: Description does not match!")
        print(f"{'='*60}\n")
        return False

if __name__ == "__main__":
    try:
        success = test_description_upload()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
