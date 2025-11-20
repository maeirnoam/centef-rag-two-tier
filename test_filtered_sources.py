"""
Test that sources are filtered to only show explicitly cited documents.
"""
import requests
import json

API_URL = "http://localhost:8001"
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJleHAiOjE3NjM2Mzg1ODR9.5EuSPbVuTGPmuQFmMra_9weXtKdEow0zlr7BZb8rglE"

def test_filtered_sources():
    """Test that only cited sources appear in the sources list"""
    
    print("=" * 80)
    print("TESTING FILTERED SOURCES")
    print("=" * 80)
    
    # Create session
    print("\n1. Creating new chat session...")
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
    response = requests.post(f"{API_URL}/chat/sessions", headers=headers)
    
    if response.status_code not in [200, 201]:
        print(f"❌ Failed to create session: {response.status_code}")
        print(response.text)
        return
    
    session_id = response.json()["session_id"]
    print(f"✓ Created session: {session_id}")
    
    # Ask a question
    print("\n2. Testing source filtering...")
    query = "What are the main methods used in terrorism financing?"
    
    print(f"\nQuery: {query}")
    
    response = requests.post(
        f"{API_URL}/chat",
        headers=headers,
        json={
            "query": query,
            "session_id": session_id,
            "max_chunks": 20,
            "max_summaries": 10
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Chat failed: {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    answer = data["answer"]
    sources = data.get("sources", [])
    explicit_citations = data.get("explicit_citations", [])
    
    print(f"\n✓ Received answer ({len(answer)} chars)")
    
    # Check answer format
    print("\n" + "=" * 80)
    print("ANSWER:")
    print("=" * 80)
    print(answer[:500] + "..." if len(answer) > 500 else answer)
    
    # Check for old citation format
    has_citations_section = "---CITATIONS---" in answer
    has_cited_sources = "CITED SOURCES:" in answer
    has_further_reading = "FOR FURTHER READING:" in answer
    
    print("\n" + "=" * 80)
    print("FORMAT CHECK:")
    print("=" * 80)
    if has_citations_section:
        print("⚠ Answer contains '---CITATIONS---' section (should be removed)")
    else:
        print("✓ No '---CITATIONS---' section (correct)")
    
    if has_cited_sources or has_further_reading:
        print("⚠ Answer contains 'CITED SOURCES' or 'FOR FURTHER READING' (should be removed)")
    else:
        print("✓ No citation enforcement sections (correct)")
    
    # Check inline citations
    print("\n" + "=" * 80)
    print("INLINE CITATIONS:")
    print("=" * 80)
    print(f"Found {len(explicit_citations)} inline citations:")
    for i, citation in enumerate(explicit_citations[:5], 1):
        print(f"  [{i}] {citation}")
    if len(explicit_citations) > 5:
        print(f"  ... and {len(explicit_citations) - 5} more")
    
    # Check sources
    print("\n" + "=" * 80)
    print("SOURCES RETURNED:")
    print("=" * 80)
    print(f"Total sources: {len(sources)}")
    
    if sources:
        print("\nSources in response:")
        for i, source in enumerate(sources, 1):
            title = source.get('title', 'Unknown')
            page_range = source.get('page_range', '')
            page_info = f" (Pages {page_range})" if page_range else ""
            print(f"  {i}. {title}{page_info}")
        
        # Verify each source appears in inline citations
        print("\n" + "=" * 80)
        print("VERIFICATION:")
        print("=" * 80)
        
        all_citations_text = " ".join(explicit_citations).lower()
        for source in sources:
            source_title = source['title'].lower()
            if source_title in all_citations_text:
                print(f"✓ '{source['title']}' found in citations")
            else:
                print(f"⚠ '{source['title']}' NOT found in citations (may be filtered incorrectly)")
    else:
        print("⚠ No sources returned")
    
    # Check follow-up questions
    follow_up_questions = data.get("follow_up_questions", [])
    print("\n" + "=" * 80)
    print("FOLLOW-UP QUESTIONS:")
    print("=" * 80)
    if follow_up_questions:
        print(f"Generated {len(follow_up_questions)} follow-up questions:")
        for i, q in enumerate(follow_up_questions, 1):
            print(f"  {i}. {q}")
    else:
        print("⚠ No follow-up questions generated")
    
    # Save full output
    output_file = "test_filtered_sources_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Full output saved to {output_file}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_filtered_sources()
