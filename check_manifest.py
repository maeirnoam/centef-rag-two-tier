"""Quick script to check manifest entries."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.manifest import get_manifest_entries

entries = get_manifest_entries()

print(f"\n{'='*80}")
print(f"Total documents in manifest: {len(entries)}")
print(f"{'='*80}\n")

for entry in entries:
    print(f"Source ID: {entry.source_id}")
    print(f"  Filename: {entry.filename}")
    print(f"  Status: {entry.status}")
    print(f"  Tags: {entry.tags}")
    if entry.author or entry.organization or entry.date:
        print(f"  Metadata:")
        if entry.author:
            print(f"    Author: {entry.author}")
        if entry.organization:
            print(f"    Organization: {entry.organization}")
        if entry.date:
            print(f"    Date: {entry.date}")
    print()
