"""
Test conversation memory feature - verify that the chat maintains context across messages.
"""
import requests
import json
import time

API_URL = "http://localhost:8001"
# Valid JWT token (expires in ~2 years)
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJleHAiOjE3NjM2Mjk0NjN9.Ne2Z0WU6E6tZbqy5fJFURfXN8tvNTnGOMt76FgfQ424"

def test_conversation_memory():
    """Test that conversation history is used for context"""
    
    print("=" * 80)
    print("TESTING CONVERSATION MEMORY")
    print("=" * 80)
    
    # Step 1: Create a new session
    print("\n1. Creating new chat session...")
    response = requests.post(
        f"{API_URL}/chat/sessions",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    
    if response.status_code not in [200, 201]:
        print(f"Failed to create session: {response.status_code}")
        print(response.text)
        return
    
    session = response.json()
    session_id = session['session_id']
    print(f"✓ Created session: {session_id}")
    
    # Step 2: Ask initial question about a specific topic
    print("\n2. Asking initial question about AML...")
    query1 = "What is AML and why is it important?"
    
    response = requests.post(
        f"{API_URL}/chat",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={
            "query": query1,
            "session_id": session_id,
            "use_optimizations": True
        }
    )
    
    if response.status_code != 200:
        print(f"Failed to send message: {response.status_code}")
        print(response.text)
        return
    
    result1 = response.json()
    print(f"\nQuery: {query1}")
    print(f"Answer (first 200 chars): {result1['answer'][:200]}...")
    print(f"Sources used: {len(result1.get('sources', []))}")
    
    time.sleep(1)  # Brief pause between messages
    
    # Step 3: Ask a follow-up question that requires context from previous answer
    print("\n3. Asking follow-up question (requires context)...")
    query2 = "Can you elaborate more on that? Give me specific examples."
    
    response = requests.post(
        f"{API_URL}/chat",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={
            "query": query2,
            "session_id": session_id,
            "use_optimizations": True
        }
    )
    
    if response.status_code != 200:
        print(f"Failed to send message: {response.status_code}")
        print(response.text)
        return
    
    result2 = response.json()
    print(f"\nQuery: {query2}")
    print(f"Answer (first 300 chars): {result2['answer'][:300]}...")
    print(f"Sources used: {len(result2.get('sources', []))}")
    
    # Check if the answer demonstrates contextual awareness
    answer_lower = result2['answer'].lower()
    has_context = any(keyword in answer_lower for keyword in ['aml', 'money laundering', 'previous', 'mentioned', 'discussed'])
    
    if has_context:
        print("\n✓ SUCCESS: Answer shows awareness of previous conversation context!")
    else:
        print("\n⚠ WARNING: Answer may not be using conversation history effectively")
    
    time.sleep(1)
    
    # Step 4: Another follow-up with pronoun reference
    print("\n4. Asking question with pronoun reference...")
    query3 = "What are the main challenges in implementing it?"
    
    response = requests.post(
        f"{API_URL}/chat",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={
            "query": query3,
            "session_id": session_id,
            "use_optimizations": True
        }
    )
    
    if response.status_code != 200:
        print(f"Failed to send message: {response.status_code}")
        print(response.text)
        return
    
    result3 = response.json()
    print(f"\nQuery: {query3}")
    print(f"Answer (first 300 chars): {result3['answer'][:300]}...")
    print(f"Sources used: {len(result3.get('sources', []))}")
    
    # Step 5: Verify conversation history endpoint
    print("\n5. Retrieving full conversation history...")
    response = requests.get(
        f"{API_URL}/chat/history/{session_id}",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    
    if response.status_code == 200:
        messages = response.json()
        print(f"\n✓ Retrieved {len(messages)} messages from history")
        
        # Should have 6 messages (3 user + 3 assistant)
        if len(messages) == 6:
            print("✓ Correct number of messages in history")
            
            print("\nConversation summary:")
            for i, msg in enumerate(messages, 1):
                role = msg['role'].upper()
                content_preview = msg['content'][:80] + "..." if len(msg['content']) > 80 else msg['content']
                print(f"  {i}. {role}: {content_preview}")
        else:
            print(f"⚠ Expected 6 messages, got {len(messages)}")
    else:
        print(f"Failed to get history: {response.status_code}")
    
    print("\n" + "=" * 80)
    print("CONVERSATION MEMORY TEST COMPLETE")
    print("=" * 80)
    
    return session_id


if __name__ == "__main__":
    test_conversation_memory()
