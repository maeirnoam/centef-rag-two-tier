"""
Simple re-index helper - lists documents and provides commands.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import get_manifest_entries, update_manifest_entry

print("="*80)
print("  Documents Ready for Re-indexing")
print("="*80)
print()

# Get all documents
entries = get_manifest_entries()

# Filter for documents that have been processed
ready_entries = [
    e for e in entries 
    if e.status in ['ready', 'embedded', 'pending_embedding'] 
    and e.data_path 
    and e.summary_path
]

if not ready_entries:
    print("⚠️  No documents found ready for indexing")
    print()
    
    # Show what we have
    status_counts = {}
    for e in entries:
        status = e.status
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("Current document statuses:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    
    sys.exit(0)

print(f"Found {len(ready_entries)} documents:")
print()

for i, entry in enumerate(ready_entries, 1):
    print(f"{i}. {entry.source_id}")
    print(f"   Title: {entry.title}")
    print(f"   Status: {entry.status}")
    print(f"   Has chunks: {'✅' if entry.data_path else '❌'}")
    print(f"   Has summary: {'✅' if entry.summary_path else '❌'}")
    print()

print("="*80)
print("To re-index these documents:")
print("="*80)
print()
print("Option 1: Re-index ALL documents")
print("  Run this PowerShell loop:")
print()
print("  $docs = @(")
for entry in ready_entries:
    print(f'    "{entry.source_id}",')
print("  )")
print("  foreach ($doc in $docs) {")
print("    Write-Host \"Indexing $doc...\" -ForegroundColor Cyan")
print("    python services/embedding/index_documents.py --source-id $doc")
print("    if ($LASTEXITCODE -eq 0) {")
print("      Write-Host \"  ✅ Success\" -ForegroundColor Green")
print("    } else {")
print("      Write-Host \"  ❌ Failed\" -ForegroundColor Red")
print("    }")
print("  }")
print()
print("Option 2: Re-index ONE document")
print("  python services/embedding/index_documents.py --source-id <source_id>")
print()
print(f"First document example:")
if ready_entries:
    print(f"  python services/embedding/index_documents.py --source-id {ready_entries[0].source_id}")
