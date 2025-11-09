"""
Test script for Vertex AI Search retrieval.
Tests the two-tier search functionality.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded environment from {env_path}")
else:
    print(f"⚠️  No .env file found at {env_path}")

# Import search functions
from apps.agent_api.retriever_vertex_search import (
    search_chunks,
    search_summaries,
    search_two_tier,
    retrieve_by_source_id
)


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_chunk_search(query: str):
    """Test searching the chunk datastore."""
    print_section(f"Testing Chunk Search: '{query}'")
    
    try:
        results = search_chunks(query, max_results=5)
        
        print(f"✅ Found {len(results)} chunk results\n")
        
        for i, result in enumerate(results, 1):
            print(f"[Chunk {i}] {result.get('title', 'Untitled')}")
            print(f"  Source ID: {result.get('source_id')}")
            print(f"  Filename: {result.get('filename')}")
            
            if result.get('page'):
                print(f"  Page: {result['page']}")
            elif result.get('start_sec') is not None:
                print(f"  Time: {result['start_sec']:.1f}s - {result.get('end_sec', 0):.1f}s")
            
            print(f"  Score: {result.get('score', 0):.4f}")
            
            content = result.get('content', '')
            content_preview = content[:200] + "..." if len(content) > 200 else content
            print(f"  Content: {content_preview}")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_summary_search(query: str):
    """Test searching the summary datastore."""
    print_section(f"Testing Summary Search: '{query}'")
    
    try:
        results = search_summaries(query, max_results=3)
        
        print(f"✅ Found {len(results)} summary results\n")
        
        for i, result in enumerate(results, 1):
            print(f"[Summary {i}] {result.get('title', 'Untitled')}")
            print(f"  Source ID: {result.get('source_id')}")
            print(f"  Filename: {result.get('filename')}")
            
            if result.get('author'):
                print(f"  Author: {result['author']}")
            if result.get('organization'):
                print(f"  Organization: {result['organization']}")
            if result.get('tags'):
                print(f"  Tags: {', '.join(result['tags'])}")
            
            print(f"  Score: {result.get('score', 0):.4f}")
            
            summary = result.get('summary_text', '')
            summary_preview = summary[:300] + "..." if len(summary) > 300 else summary
            print(f"  Summary: {summary_preview}")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_two_tier_search(query: str):
    """Test combined two-tier search."""
    print_section(f"Testing Two-Tier Search: '{query}'")
    
    try:
        results = search_two_tier(query, max_chunk_results=5, max_summary_results=2)
        
        print(f"✅ Two-tier search completed")
        print(f"  - Summaries: {results['total_summaries']}")
        print(f"  - Chunks: {results['total_chunks']}")
        print()
        
        # Show summary results
        if results['summaries']:
            print("📄 Summary Results:")
            for i, summary in enumerate(results['summaries'], 1):
                print(f"  [{i}] {summary.get('title', 'Untitled')} (score: {summary.get('score', 0):.4f})")
        
        # Show chunk results
        if results['chunks']:
            print("\n📝 Chunk Results:")
            for i, chunk in enumerate(results['chunks'], 1):
                location = f"page {chunk['page']}" if chunk.get('page') else f"{chunk.get('start_sec', 0):.1f}s"
                print(f"  [{i}] {chunk.get('title', 'Untitled')} - {location} (score: {chunk.get('score', 0):.4f})")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_retrieve_by_source_id(source_id: str):
    """Test retrieving all content for a specific source."""
    print_section(f"Testing Retrieve by Source ID: '{source_id}'")
    
    try:
        results = retrieve_by_source_id(source_id)
        
        print(f"✅ Retrieved content for source_id: {source_id}")
        print(f"  - Total chunks: {results['total_chunks']}")
        print(f"  - Has summary: {'Yes' if results['summary'] else 'No'}")
        
        if results['summary']:
            summary = results['summary']
            print(f"\n📄 Summary:")
            print(f"  Title: {summary.get('title')}")
            print(f"  Filename: {summary.get('filename')}")
            if summary.get('author'):
                print(f"  Author: {summary['author']}")
        
        if results['chunks']:
            print(f"\n📝 First 3 chunks:")
            for i, chunk in enumerate(results['chunks'][:3], 1):
                location = f"page {chunk['page']}" if chunk.get('page') else f"{chunk.get('start_sec', 0):.1f}s"
                print(f"  [{i}] {location}: {chunk.get('content', '')[:100]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def check_environment():
    """Check environment configuration."""
    print_section("Environment Configuration")
    
    required_vars = [
        "PROJECT_ID",
        "CHUNKS_DATASTORE_ID",
        "SUMMARIES_DATASTORE_ID",
        "VERTEX_SEARCH_LOCATION"
    ]
    
    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Truncate long values for display
            display_value = value if len(value) < 60 else value[:57] + "..."
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: NOT SET")
            all_set = False
    
    if not all_set:
        print("\n⚠️  Please set all required environment variables in .env file")
        return False
    
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  CENTEF RAG - Two-Tier Search Test")
    print("=" * 80)
    
    # Check environment
    if not check_environment():
        print("\n❌ Environment not configured properly. Exiting.")
        return
    
    # Get test query from user
    print("\n")
    test_query = input("Enter a search query (or press Enter for default): ").strip()
    
    if not test_query:
        test_query = "climate change"
        print(f"Using default query: '{test_query}'")
    
    # Run tests
    test_chunk_search(test_query)
    test_summary_search(test_query)
    test_two_tier_search(test_query)
    
    # Optionally test retrieve by source_id
    print("\n")
    source_id = input("Enter a source_id to retrieve (or press Enter to skip): ").strip()
    if source_id:
        test_retrieve_by_source_id(source_id)
    
    print("\n" + "=" * 80)
    print("  Tests Complete")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
