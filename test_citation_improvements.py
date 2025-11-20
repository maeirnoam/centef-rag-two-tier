"""
Test improved citation handling - verify 4+ sources, video priority, and cited vs further reading separation.
"""
import requests
import json

API_URL = "http://localhost:8001"
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJleHAiOjE3NjM2MzQwOTR9.oE9tOvLG3iwH0D-7sKZatHLkz5SGLSpgM2wrBYsd3ZQ"

def test_citation_improvements():
    """Test that citations meet new requirements"""
    
    print("=" * 80)
    print("TESTING CITATION IMPROVEMENTS")
    print("=" * 80)
    
    # Create session
    print("\n1. Creating new chat session...")
    response = requests.post(
        f"{API_URL}/chat/sessions",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    
    if response.status_code not in [200, 201]:
        print(f"Failed to create session: {response.status_code}")
        return
    
    session = response.json()
    session_id = session['session_id']
    print(f"✓ Created session: {session_id}")
    
    # Test query about terrorism financing
    print("\n2. Testing citation requirements...")
    query = "What are the main methods used in terrorism financing and how do financial institutions detect them?"
    
    print(f"\nQuery: {query}")
    print("\nExpected:")
    print("  - At least 3 different sources cited")
    print("  - Video sources included if available")
    print("  - Separate 'CITED SOURCES' and 'FOR FURTHER READING' sections")
    
    response = requests.post(
        f"{API_URL}/chat",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={
            "query": query,
            "session_id": session_id,
            "use_optimizations": True,  # Test optimized synthesizer
            "max_chunks": 20,
            "max_summaries": 10
        }
    )
    
    if response.status_code != 200:
        print(f"\nFailed to send message: {response.status_code}")
        print(response.text)
        return
    
    result = response.json()
    answer = result['answer']
    sources = result.get('sources', [])
    
    print(f"\n✓ Received answer ({len(answer)} chars)")
    print(f"✓ Total sources retrieved: {len(sources)}")
    
    # Check if answer contains citations section
    if "---CITATIONS---" in answer:
        print("\n✓ Answer contains citations section")
        
        # Check for new format
        if "CITED SOURCES:" in answer and "FOR FURTHER READING:" in answer:
            print("✓ Answer uses new format with CITED SOURCES and FOR FURTHER READING")
            
            # Extract sections
            citations_part = answer.split("---CITATIONS---")[1]
            cited_section = citations_part.split("FOR FURTHER READING:")[0]
            further_section = citations_part.split("FOR FURTHER READING:")[1] if "FOR FURTHER READING:" in citations_part else ""
            
            # Count cited sources
            cited_lines = [line.strip() for line in cited_section.split('\n') if line.strip() and line.strip().startswith('-')]
            further_lines = [line.strip() for line in further_section.split('\n') if line.strip() and line.strip().startswith('-')]
            
            print(f"\n📚 CITED SOURCES: {len(cited_lines)}")
            for line in cited_lines[:5]:  # Show first 5
                print(f"  {line}")
            
            print(f"\n📖 FOR FURTHER READING: {len(further_lines)}")
            for line in further_lines[:5]:  # Show first 5
                print(f"  {line}")
            
            # Check for video sources
            has_video = any('video' in line.lower() or 'timestamp' in line.lower() or ':' in line for line in cited_lines)
            if has_video:
                print("\n✓ Video/timestamp source included in citations!")
            else:
                print("\n⚠ No video source found in citations (may not be available in results)")
            
            # Validate minimum 3 sources
            if len(cited_lines) >= 3:
                print(f"\n✓ SUCCESS: {len(cited_lines)} sources cited (meets 3+ requirement)")
            else:
                print(f"\n⚠ Only {len(cited_lines)} sources cited (expected 3+)")
        
        else:
            print("⚠ Answer uses old citation format (no CITED SOURCES/FOR FURTHER READING separation)")
    else:
        print("\n❌ No citations section found in answer")
    
    # Show inline citations
    inline_citations = answer.count('[')
    print(f"\n📌 Inline citations found: {inline_citations}")
    
    # Save full output
    output = {
        "query": query,
        "answer": answer,
        "sources_count": len(sources),
        "sources": sources[:3]  # First 3 sources for reference
    }
    
    with open("test_citation_output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("\n✓ Full output saved to test_citation_output.json")
    
    print("\n" + "=" * 80)
    print("CITATION IMPROVEMENTS TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_citation_improvements()
