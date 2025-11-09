"""
Test the complete RAG pipeline: Search + Synthesis.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from apps.agent_api.retriever_vertex_search import search_two_tier
from apps.agent_api.synthesizer import synthesize_answer

# Test query
query = "what recent events took place by CENTEF?"

print(f"\n{'='*80}")
print(f"COMPLETE RAG PIPELINE TEST")
print(f"{'='*80}")
print(f"\nQuery: {query}")
print()

# Step 1: Retrieve relevant documents
print("[1/2] Retrieving relevant documents...")
print("-" * 80)

try:
    results = search_two_tier(query, max_chunk_results=5, max_summary_results=3)
    
    summaries = results.get('summaries', [])
    chunks = results.get('chunks', [])
    
    print(f"✅ Found {len(summaries)} summaries and {len(chunks)} chunks")
    print()
    
    # Show what we found
    print("Summaries:")
    for i, s in enumerate(summaries, 1):
        print(f"  {i}. {s.get('title', 'Unknown')}")
    
    print("\nChunks:")
    for i, c in enumerate(chunks, 1):
        page = f" (Page {c.get('page_number', '?')})" if c.get('page_number') else ""
        print(f"  {i}. {c.get('title', 'Unknown')}{page}")
    
except Exception as e:
    print(f"❌ Error during retrieval: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Synthesize answer with Gemini
print()
print("[2/2] Synthesizing answer with Gemini...")
print("-" * 80)

try:
    synthesis_result = synthesize_answer(
        query=query,
        summary_results=summaries,
        chunk_results=chunks,
        temperature=0.2
    )
    
    print(f"✅ Answer generated")
    print()
    
    # Display the answer
    print("="*80)
    print("ANSWER:")
    print("="*80)
    print()
    print(synthesis_result['answer'])
    print()
    
    # Display metadata
    print("="*80)
    print("METADATA:")
    print("="*80)
    print(f"Model: {synthesis_result['model']}")
    print(f"Temperature: {synthesis_result['temperature']}")
    print(f"Summaries used: {synthesis_result['num_summaries_used']}")
    print(f"Chunks used: {synthesis_result['num_chunks_used']}")
    print()
    
    # Display sources
    print("SOURCES:")
    for i, source in enumerate(synthesis_result['sources'], 1):
        print(f"  {i}. {source['title']} ({source['type']})")
        if source.get('page'):
            print(f"     Page: {source['page']}")
    
    print()
    print("="*80)
    print("✅ Complete RAG pipeline test successful!")
    print("="*80)
    
except Exception as e:
    print(f"❌ Error during synthesis: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
