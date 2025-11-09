"""
Interactive query interface for the RAG system.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from apps.agent_api.retriever_vertex_search import search_two_tier
from apps.agent_api.synthesizer import synthesize_answer


def run_query(query: str, max_chunks: int = 5, max_summaries: int = 3, temperature: float = 0.2):
    """Run a single query through the RAG pipeline."""
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}\n")
    
    # Step 1: Retrieve
    print("[1/2] Searching...")
    try:
        results = search_two_tier(query, max_chunk_results=max_chunks, max_summary_results=max_summaries)
        summaries = results.get('summaries', [])
        chunks = results.get('chunks', [])
        print(f"✅ Found {len(summaries)} summaries and {len(chunks)} chunks\n")
    except Exception as e:
        print(f"❌ Search error: {e}\n")
        return
    
    # Step 2: Synthesize
    print("[2/2] Generating answer...")
    try:
        synthesis_result = synthesize_answer(
            query=query,
            summary_results=summaries,
            chunk_results=chunks,
            temperature=temperature
        )
        print(f"✅ Answer ready\n")
    except Exception as e:
        print(f"❌ Synthesis error: {e}\n")
        return
    
    # Display results
    print("="*80)
    print("ANSWER:")
    print("="*80)
    print()
    print(synthesis_result['answer'])
    print()
    
    # Display explicit citations
    if synthesis_result.get('explicit_citations'):
        print("="*80)
        print("EXPLICIT CITATIONS:")
        print("="*80)
        for i, citation in enumerate(synthesis_result['explicit_citations'], 1):
            print(f"  [{i}] {citation}")
        print()
    
    # Display all sources used for context
    if synthesis_result['sources']:
        print("="*80)
        print("ALL SOURCES USED FOR CONTEXT:")
        print("="*80)
        for i, source in enumerate(synthesis_result['sources'], 1):
            # Format source citation
            title = source.get('title', 'Unknown')
            source_type = source.get('type', 'unknown')
            
            # Add page range if available
            page_info = ""
            if source.get('page_range'):
                page_info = f" (Pages {source['page_range']})"
            elif source.get('pages'):
                # Fallback if page_range wasn't formatted
                pages = source['pages']
                if len(pages) == 1:
                    page_info = f" (Page {pages[0]})"
                else:
                    page_info = f" (Pages {', '.join(map(str, pages))})"
            
            # Add timestamps for audio/video
            if source.get('timestamps'):
                timestamps = source['timestamps']
                if len(timestamps) == 1:
                    t = timestamps[0]
                    page_info = f" ({t['start']} - {t['end']})"
                else:
                    page_info = f" (Multiple segments)"
            
            print(f"  {i}. {title}{page_info} [{source_type}]")
        print()


def interactive_mode():
    """Run in interactive mode with continuous queries."""
    print("\n" + "="*80)
    print("CENTEF RAG System - Interactive Query Mode")
    print("="*80)
    print("\nCommands:")
    print("  - Type your question and press Enter")
    print("  - Type 'quit' or 'exit' to quit")
    print("  - Type 'settings' to adjust retrieval parameters")
    print()
    
    # Default settings
    max_chunks = 8
    max_summaries = 3
    temperature = 0.2
    
    while True:
        try:
            query = input("Your question: ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            if query.lower() == 'settings':
                print("\nCurrent settings:")
                print(f"  Max chunks: {max_chunks}")
                print(f"  Max summaries: {max_summaries}")
                print(f"  Temperature: {temperature}")
                print()
                
                try:
                    chunks_input = input(f"Max chunks [{max_chunks}]: ").strip()
                    if chunks_input:
                        max_chunks = int(chunks_input)
                    
                    summaries_input = input(f"Max summaries [{max_summaries}]: ").strip()
                    if summaries_input:
                        max_summaries = int(summaries_input)
                    
                    temp_input = input(f"Temperature [{temperature}]: ").strip()
                    if temp_input:
                        temperature = float(temp_input)
                    
                    print("\n✅ Settings updated\n")
                except ValueError as e:
                    print(f"\n❌ Invalid input: {e}\n")
                
                continue
            
            # Run the query
            run_query(query, max_chunks=max_chunks, max_summaries=max_summaries, temperature=temperature)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def single_query_mode():
    """Run a single query from command line."""
    if len(sys.argv) < 2:
        print("Usage: python query.py \"your question here\"")
        print("   or: python query.py          (for interactive mode)")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    run_query(query)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        single_query_mode()
    else:
        interactive_mode()
