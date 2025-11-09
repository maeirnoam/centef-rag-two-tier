"""
Quick test for "what is CTF?" query.
Run after authenticating with: gcloud auth application-default login
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from apps.agent_api.retriever_vertex_search import search_two_tier

# Test query
query = "what is AML?"
print(f"\n🔍 Searching for: '{query}'")
print("=" * 80)

try:
    results = search_two_tier(query, max_chunk_results=5, max_summary_results=3)
    
    print(f"\n✅ Search completed successfully!")
    print(f"   Summaries found: {results['total_summaries']}")
    print(f"   Chunks found: {results['total_chunks']}")
    
    # Display summaries
    if results['summaries']:
        print(f"\n📄 DOCUMENT SUMMARIES ({len(results['summaries'])} results):")
        print("=" * 80)
        for i, summary in enumerate(results['summaries'], 1):
            print(f"\n[{i}] {summary.get('title', 'Untitled')}")
            print(f"    File: {summary.get('filename', 'N/A')}")
            print(f"    Score: {summary.get('score', 0):.4f}")
            if summary.get('author'):
                print(f"    Author: {summary['author']}")
            if summary.get('organization'):
                print(f"    Organization: {summary['organization']}")
            if summary.get('tags'):
                print(f"    Tags: {', '.join(summary['tags'])}")
            
            summary_text = summary.get('summary_text', '')
            preview = summary_text[:500] + "..." if len(summary_text) > 500 else summary_text
            print(f"\n    Summary:\n    {preview}")
    else:
        print("\n⚠️  No summaries found")
    
    # Display chunks
    if results['chunks']:
        print(f"\n\n📝 DETAILED CHUNKS ({len(results['chunks'])} results):")
        print("=" * 80)
        for i, chunk in enumerate(results['chunks'], 1):
            print(f"\n[{i}] {chunk.get('title', 'Untitled')}")
            print(f"    File: {chunk.get('filename', 'N/A')}")
            
            # Location info
            if chunk.get('page'):
                print(f"    Location: Page {chunk['page']}")
            elif chunk.get('start_sec') is not None:
                start = chunk['start_sec']
                end = chunk.get('end_sec', start)
                print(f"    Location: {start:.1f}s - {end:.1f}s")
            
            print(f"    Score: {chunk.get('score', 0):.4f}")
            
            content = chunk.get('content', '')
            preview = content[:400] + "..." if len(content) > 400 else content
            print(f"\n    Content:\n    {preview}")
    else:
        print("\n⚠️  No chunks found")
    
    print("\n" + "=" * 80)
    print("✅ Test complete!\n")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nIf you see authentication errors, run:")
    print("  gcloud auth application-default login")
