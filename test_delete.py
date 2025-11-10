"""
Test cascading delete functionality.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.source_management import delete_source_completely
from shared.manifest import get_manifest_entries

# List all documents
print("="*80)
print("AVAILABLE DOCUMENTS FOR DELETION TEST")
print("="*80)

entries = get_manifest_entries()

if not entries:
    print("\n❌ No documents found in manifest")
    sys.exit(1)

print(f"\nFound {len(entries)} documents:")
for i, entry in enumerate(entries[:10], 1):  # Show first 10
    print(f"  {i}. {entry.source_id}")
    print(f"     Title: {entry.title}")
    print(f"     Status: {entry.status}")
    print(f"     Files: {entry.source_uri}")
    print()

print("\n" + "="*80)
print("⚠️  WARNING: DESTRUCTIVE TEST ⚠️")
print("="*80)
print("\nThis script is for testing the cascading delete functionality.")
print("It will PERMANENTLY delete a document and all its associated data.")
print("\nTo test:")
print("  1. Choose a test document source_id")
print("  2. Run: python test_delete.py <source_id>")
print("\nExample: python test_delete.py test-document_12345678")
print("\nThe delete will:")
print("  • Delete source file from GCS")
print("  • Delete chunks JSONL from GCS")
print("  • Delete summary JSONL from GCS")
print("  • Delete all indexed chunks from Discovery Engine")
print("  • Delete indexed summary from Discovery Engine")
print("  • Delete manifest entry")
print()

if len(sys.argv) < 2:
    print("No source_id provided. Exiting safely.")
    sys.exit(0)

source_id = sys.argv[1]

print(f"\n{'='*80}")
print(f"DELETING: {source_id}")
print(f"{'='*80}\n")

# Find the entry
entry = next((e for e in entries if e.source_id == source_id), None)
if not entry:
    print(f"❌ Source {source_id} not found in manifest")
    sys.exit(1)

print(f"Found document:")
print(f"  Title: {entry.title}")
print(f"  Status: {entry.status}")
print(f"  Source: {entry.source_uri}")
print(f"  Chunks: {entry.data_path}")
print(f"  Summary: {entry.summary_path}")
print()

# Final confirmation
confirmation = input(f"Type 'DELETE' to confirm deletion of {source_id}: ").strip()

if confirmation != 'DELETE':
    print("\n❌ Deletion cancelled")
    sys.exit(0)

print("\n🗑️  Starting cascading deletion...")
print()

# Perform deletion
result = delete_source_completely(source_id)

print(f"\n{'='*80}")
print("DELETION RESULT")
print(f"{'='*80}\n")

print(f"Success: {result['success']}")
print()
print("Deleted:")
print(f"  • Source file: {'✓' if result['deleted']['source_file'] else '✗'}")
print(f"  • Chunks file: {'✓' if result['deleted']['chunks_file'] else '✗'}")
print(f"  • Summary file: {'✓' if result['deleted']['summary_file'] else '✗'}")
print(f"  • Indexed chunks: {result['deleted']['indexed_chunks']} documents")
print(f"  • Indexed summary: {'✓' if result['deleted']['indexed_summary'] else '✗'}")
print(f"  • Manifest entry: {'✓' if result['deleted']['manifest_entry'] else '✗'}")

if result['errors']:
    print("\nErrors:")
    for error in result['errors']:
        print(f"  • {error}")

print()

if result['success']:
    print("✅ Cascading delete completed successfully")
else:
    print("⚠️  Cascading delete completed with errors")
