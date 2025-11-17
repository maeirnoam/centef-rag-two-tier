"""
Test script for the user feedback system.
Tests the backend functionality for chat message feedback.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared.chat_history import (
    ChatMessage,
    MessageRole,
    save_message,
    get_conversation_history,
    update_message_feedback,
    create_new_session
)
import uuid
from datetime import datetime

def test_feedback_system():
    """Test the feedback system end-to-end."""

    print("=" * 60)
    print("Testing Chat Feedback System")
    print("=" * 60)

    # Test user
    test_user_id = "test_user_feedback"

    try:
        # 1. Create a new session
        print("\n1. Creating test session...")
        session = create_new_session(test_user_id, title="Feedback Test Session")
        session_id = session.session_id
        print(f"   ✓ Session created: {session_id}")

        # 2. Create test messages
        print("\n2. Creating test messages...")

        # User message
        user_msg = ChatMessage(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=test_user_id,
            role=MessageRole.USER,
            content="What is terrorism financing?"
        )
        save_message(user_msg)
        print(f"   ✓ User message saved: {user_msg.message_id}")

        # Assistant message
        assistant_msg = ChatMessage(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=test_user_id,
            role=MessageRole.ASSISTANT,
            content="Terrorism financing refers to the methods and sources used to fund terrorist activities...",
            sources=[{"title": "Test Source", "page": 1}],
            citations=["Test Citation"],
            model_used="gemini-1.5-pro"
        )
        save_message(assistant_msg)
        print(f"   ✓ Assistant message saved: {assistant_msg.message_id}")

        # 3. Test thumbs up feedback
        print("\n3. Testing thumbs up feedback...")
        success = update_message_feedback(
            user_id=test_user_id,
            session_id=session_id,
            message_id=assistant_msg.message_id,
            feedback_rating="thumbs_up"
        )
        assert success, "Failed to update thumbs up feedback"
        print("   ✓ Thumbs up feedback saved")

        # Verify feedback was saved
        messages = get_conversation_history(test_user_id, session_id)
        assistant_msg_updated = next((m for m in messages if m.role == MessageRole.ASSISTANT), None)
        assert assistant_msg_updated is not None, "Assistant message not found"
        assert assistant_msg_updated.feedback_rating == "thumbs_up", "Feedback rating not saved correctly"
        assert assistant_msg_updated.feedback_timestamp is not None, "Feedback timestamp not set"
        print(f"   ✓ Feedback verified: {assistant_msg_updated.feedback_rating}")

        # 4. Test thumbs down with note
        print("\n4. Testing thumbs down feedback with note...")
        success = update_message_feedback(
            user_id=test_user_id,
            session_id=session_id,
            message_id=assistant_msg.message_id,
            feedback_rating="thumbs_down",
            feedback_note="The response was too generic and didn't cite specific sources."
        )
        assert success, "Failed to update thumbs down feedback"
        print("   ✓ Thumbs down feedback with note saved")

        # Verify feedback with note was saved
        messages = get_conversation_history(test_user_id, session_id)
        assistant_msg_updated = next((m for m in messages if m.role == MessageRole.ASSISTANT), None)
        assert assistant_msg_updated.feedback_rating == "thumbs_down", "Feedback rating not updated"
        assert assistant_msg_updated.feedback_note == "The response was too generic and didn't cite specific sources.", "Feedback note not saved"
        print(f"   ✓ Feedback verified: {assistant_msg_updated.feedback_rating}")
        print(f"   ✓ Note verified: {assistant_msg_updated.feedback_note}")

        # 5. Test updating feedback (changing from thumbs down to thumbs up)
        print("\n5. Testing feedback update (thumbs down -> thumbs up)...")
        success = update_message_feedback(
            user_id=test_user_id,
            session_id=session_id,
            message_id=assistant_msg.message_id,
            feedback_rating="thumbs_up",
            feedback_note="Actually, upon reflection, this was helpful."
        )
        assert success, "Failed to update feedback"
        print("   ✓ Feedback updated")

        # Verify updated feedback
        messages = get_conversation_history(test_user_id, session_id)
        assistant_msg_updated = next((m for m in messages if m.role == MessageRole.ASSISTANT), None)
        assert assistant_msg_updated.feedback_rating == "thumbs_up", "Feedback rating not updated correctly"
        assert assistant_msg_updated.feedback_note == "Actually, upon reflection, this was helpful.", "Feedback note not updated"
        print(f"   ✓ Updated feedback verified: {assistant_msg_updated.feedback_rating}")
        print(f"   ✓ Updated note verified: {assistant_msg_updated.feedback_note}")

        # 6. Test feedback persistence
        print("\n6. Testing feedback persistence (reload from storage)...")
        messages_reloaded = get_conversation_history(test_user_id, session_id)
        assistant_msg_reloaded = next((m for m in messages_reloaded if m.role == MessageRole.ASSISTANT), None)
        assert assistant_msg_reloaded.feedback_rating == "thumbs_up", "Feedback not persisted"
        assert assistant_msg_reloaded.feedback_note is not None, "Feedback note not persisted"
        assert assistant_msg_reloaded.feedback_timestamp is not None, "Feedback timestamp not persisted"
        print("   ✓ Feedback persisted correctly")

        # 7. Test invalid message ID
        print("\n7. Testing invalid message ID...")
        success = update_message_feedback(
            user_id=test_user_id,
            session_id=session_id,
            message_id="invalid-message-id",
            feedback_rating="thumbs_up"
        )
        assert not success, "Should fail with invalid message ID"
        print("   ✓ Invalid message ID handled correctly")

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print(f"\nTest session ID: {session_id}")
        print(f"Test user ID: {test_user_id}")
        print("\nYou can view this session in the chat interface to see the feedback UI.")

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_feedback_system()
    sys.exit(0 if success else 1)
