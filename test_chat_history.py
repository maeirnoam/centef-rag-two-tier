"""
Test script for chat history and conversation management.

Tests:
1. Basic chat history operations (save, retrieve)
2. Multi-user isolation
3. Session management
4. Message ordering and filtering
"""
import sys
from pathlib import Path
import uuid

sys.path.insert(0, str(Path(__file__).parent))

from shared.chat_history import (
    ChatMessage,
    ConversationSession,
    MessageRole,
    save_message,
    get_conversation_history,
    get_user_sessions,
    create_new_session,
    delete_session,
    update_session_title
)

print("=" * 80)
print("CHAT HISTORY TEST SUITE")
print("=" * 80)
print()

# Test 1: Create sessions for multiple users
print("[Test 1] Creating sessions for multiple users...")
user1_id = "test_user_1"
user2_id = "test_user_2"

session1 = create_new_session(user1_id, title="User 1 - Session 1")
session2 = create_new_session(user1_id, title="User 1 - Session 2")
session3 = create_new_session(user2_id, title="User 2 - Session 1")

print(f"  ✅ Created session {session1.session_id} for {user1_id}")
print(f"  ✅ Created session {session2.session_id} for {user1_id}")
print(f"  ✅ Created session {session3.session_id} for {user2_id}")
print()

# Test 2: Add messages to conversations
print("[Test 2] Adding messages to conversations...")

# User 1, Session 1
messages_1_1 = [
    ChatMessage(
        message_id=str(uuid.uuid4()),
        session_id=session1.session_id,
        user_id=user1_id,
        role=MessageRole.USER,
        content="What is counter-terrorism financing?"
    ),
    ChatMessage(
        message_id=str(uuid.uuid4()),
        session_id=session1.session_id,
        user_id=user1_id,
        role=MessageRole.ASSISTANT,
        content="Counter-terrorism financing (CTF) refers to measures...",
        sources=[{"title": "Test Doc", "page": 1}],
        citations=["Test Doc, Page 1"],
        model_used="gemini-2.0-flash-exp"
    ),
    ChatMessage(
        message_id=str(uuid.uuid4()),
        session_id=session1.session_id,
        user_id=user1_id,
        role=MessageRole.USER,
        content="Can you give me examples?"
    ),
    ChatMessage(
        message_id=str(uuid.uuid4()),
        session_id=session1.session_id,
        user_id=user1_id,
        role=MessageRole.ASSISTANT,
        content="Certainly! Here are some examples...",
        sources=[{"title": "Test Doc", "page": 2}],
        citations=["Test Doc, Page 2"],
        model_used="gemini-2.0-flash-exp"
    ),
]

for msg in messages_1_1:
    save_message(msg)

print(f"  ✅ Saved {len(messages_1_1)} messages for {user1_id} - Session 1")

# User 1, Session 2
messages_1_2 = [
    ChatMessage(
        message_id=str(uuid.uuid4()),
        session_id=session2.session_id,
        user_id=user1_id,
        role=MessageRole.USER,
        content="What is AML?"
    ),
    ChatMessage(
        message_id=str(uuid.uuid4()),
        session_id=session2.session_id,
        user_id=user1_id,
        role=MessageRole.ASSISTANT,
        content="AML stands for Anti-Money Laundering...",
        model_used="gemini-2.0-flash-exp"
    ),
]

for msg in messages_1_2:
    save_message(msg)

print(f"  ✅ Saved {len(messages_1_2)} messages for {user1_id} - Session 2")

# User 2, Session 1
messages_2_1 = [
    ChatMessage(
        message_id=str(uuid.uuid4()),
        session_id=session3.session_id,
        user_id=user2_id,
        role=MessageRole.USER,
        content="Different user's question"
    ),
    ChatMessage(
        message_id=str(uuid.uuid4()),
        session_id=session3.session_id,
        user_id=user2_id,
        role=MessageRole.ASSISTANT,
        content="Answer for different user...",
        model_used="gemini-2.0-flash-exp"
    ),
]

for msg in messages_2_1:
    save_message(msg)

print(f"  ✅ Saved {len(messages_2_1)} messages for {user2_id} - Session 1")
print()

# Test 3: Retrieve conversation history
print("[Test 3] Retrieving conversation history...")

history_1_1 = get_conversation_history(user1_id, session1.session_id)
print(f"  ✅ Retrieved {len(history_1_1)} messages from {user1_id} - Session 1")
assert len(history_1_1) == 4, "Should have 4 messages"

# Verify order
assert history_1_1[0].role == MessageRole.USER
assert history_1_1[1].role == MessageRole.ASSISTANT
assert history_1_1[2].role == MessageRole.USER
assert history_1_1[3].role == MessageRole.ASSISTANT
print(f"  ✅ Messages are in correct chronological order")

# Test limit parameter
history_limited = get_conversation_history(user1_id, session1.session_id, limit=2)
assert len(history_limited) == 2
assert history_limited[0].content == "Can you give me examples?"
print(f"  ✅ Limit parameter works correctly (returned {len(history_limited)} most recent)")
print()

# Test 4: Multi-user isolation
print("[Test 4] Testing multi-user isolation...")

# User 1 should only see their sessions
user1_sessions = get_user_sessions(user1_id)
print(f"  ✅ User 1 has {len(user1_sessions)} sessions")
assert len(user1_sessions) == 2, "User 1 should have 2 sessions"
assert all(s.user_id == user1_id for s in user1_sessions)

# User 2 should only see their sessions
user2_sessions = get_user_sessions(user2_id)
print(f"  ✅ User 2 has {len(user2_sessions)} sessions")
assert len(user2_sessions) == 1, "User 2 should have 1 session"
assert all(s.user_id == user2_id for s in user2_sessions)

print(f"  ✅ Multi-user isolation verified - users can only access their own data")
print()

# Test 5: Session metadata
print("[Test 5] Testing session metadata...")

sessions = get_user_sessions(user1_id)
for session in sessions:
    print(f"  Session: {session.title}")
    print(f"    ID: {session.session_id}")
    print(f"    Message count: {session.message_count}")
    print(f"    Created: {session.created_at}")
    print(f"    Updated: {session.updated_at}")

assert sessions[0].message_count > 0, "Sessions should have message counts"
print(f"  ✅ Session metadata is properly maintained")
print()

# Test 6: Update session title
print("[Test 6] Testing session title update...")

old_title = session1.title
new_title = "Updated: CTF Discussion"
updated_session = update_session_title(user1_id, session1.session_id, new_title)

assert updated_session is not None, "Session should be found"
assert updated_session.title == new_title, "Title should be updated"
print(f"  ✅ Session title updated from '{old_title}' to '{new_title}'")
print()

# Test 7: Delete session
print("[Test 7] Testing session deletion...")

# Create a temporary session to delete
temp_session = create_new_session(user1_id, title="Temporary Session")
temp_message = ChatMessage(
    message_id=str(uuid.uuid4()),
    session_id=temp_session.session_id,
    user_id=user1_id,
    role=MessageRole.USER,
    content="This will be deleted"
)
save_message(temp_message)

# Verify it exists
history_before = get_conversation_history(user1_id, temp_session.session_id)
assert len(history_before) == 1, "Temp session should have 1 message"

# Delete it
success = delete_session(user1_id, temp_session.session_id)
assert success, "Deletion should succeed"

# Verify it's gone
history_after = get_conversation_history(user1_id, temp_session.session_id)
assert len(history_after) == 0, "Temp session should be deleted"

print(f"  ✅ Session deleted successfully")
print()

# Test 8: Verify citation and source metadata
print("[Test 8] Testing citation and source metadata...")

history = get_conversation_history(user1_id, session1.session_id)
assistant_messages = [m for m in history if m.role == MessageRole.ASSISTANT]

assert len(assistant_messages) > 0, "Should have assistant messages"
assert assistant_messages[0].sources, "Assistant messages should have sources"
assert assistant_messages[0].citations, "Assistant messages should have citations"
assert assistant_messages[0].model_used, "Assistant messages should have model_used"

print(f"  ✅ First assistant message has:")
print(f"    Sources: {assistant_messages[0].sources}")
print(f"    Citations: {assistant_messages[0].citations}")
print(f"    Model: {assistant_messages[0].model_used}")
print()

print("=" * 80)
print("ALL TESTS PASSED! ✅")
print("=" * 80)
print()
print("Summary:")
print(f"  - Created and managed sessions for multiple users")
print(f"  - Verified multi-user isolation")
print(f"  - Tested message ordering and retrieval with limits")
print(f"  - Validated session metadata updates")
print(f"  - Verified citation and source metadata storage")
print()
print("Chat history system is working correctly!")
