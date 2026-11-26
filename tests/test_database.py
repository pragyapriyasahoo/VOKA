"""Tests for Voka database operations."""

import uuid

import pytest

from voka.database.postgres import PostgresDatabase
from voka.database.repositories import PersistenceService, LOCAL_USER_ID


@pytest.mark.integration
def test_create_user(persistence):
    """Test user creation and retrieval."""
    user_id = persistence.database.create_user(LOCAL_USER_ID)
    assert user_id == LOCAL_USER_ID
    
    user = persistence.database.get_user(LOCAL_USER_ID)
    assert user is not None
    assert user["id"] == LOCAL_USER_ID


@pytest.mark.integration
def test_create_character(persistence):
    """Test character creation."""
    char_id = persistence.database.create_character("TestChar")
    assert char_id is not None
    
    # Creating again should return same ID (ON CONFLICT)
    char_id2 = persistence.database.create_character("TestChar")
    assert char_id == char_id2


@pytest.mark.integration
def test_conversation_lifecycle(persistence):
    """Test conversation creation and ending."""
    user_id = persistence.database.create_user(LOCAL_USER_ID)
    char_id = persistence.database.create_character("Manya")
    
    conv_id = persistence.database.create_conversation(user_id, char_id)
    assert conv_id is not None
    
    # End conversation
    persistence.database.end_conversation(conv_id)
    
    # Verify ended_at is set
    with persistence.database._require_connection().cursor() as cur:
        cur.execute("SELECT ended_at FROM conversations WHERE id = %s", (conv_id,))
        row = cur.fetchone()
        assert row["ended_at"] is not None


@pytest.mark.integration
def test_save_and_get_messages(persistence):
    """Test saving and retrieving messages."""
    user_id = persistence.database.create_user(LOCAL_USER_ID)
    char_id = persistence.database.create_character("Manya")
    conv_id = persistence.database.create_conversation(user_id, char_id)
    
    # Save user message
    msg_id = persistence.database.save_message(conv_id, "user", "Hello", "english", "happy", 0.9)
    assert msg_id is not None
    
    # Save assistant message
    msg_id2 = persistence.database.save_message(conv_id, "assistant", "Hi there!", "english")
    assert msg_id2 is not None
    
    # Retrieve messages
    messages = persistence.database.get_recent_messages(conv_id, limit=10)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hi there!"


@pytest.mark.integration
def test_save_memory(persistence):
    """Test saving and retrieving memories."""
    user_id = persistence.database.create_user(LOCAL_USER_ID)
    char_id = persistence.database.create_character("Manya")
    
    mem_id = persistence.database.save_memory(user_id, char_id, "preference", "I like apples", importance=1.0)
    assert mem_id is not None
    
    memories = persistence.database.get_memories(user_id, char_id, limit=10)
    assert len(memories) == 1
    assert memories[0]["content"] == "I like apples"
    assert memories[0]["memory_type"] == "preference"


@pytest.mark.integration
def test_memory_dedup(persistence):
    """Test memory deduplication constraint."""
    user_id = persistence.database.create_user(LOCAL_USER_ID)
    char_id = persistence.database.create_character("Manya")
    
    # Save same memory twice
    mem_id1 = persistence.database.save_memory(user_id, char_id, "preference", "I like apples", importance=1.0)
    mem_id2 = persistence.database.save_memory(user_id, char_id, "preference", "I like apples", importance=1.0)
    
    # Second insert should return None due to ON CONFLICT DO NOTHING
    assert mem_id2 is None
    
    memories = persistence.database.get_memories(user_id, char_id, limit=10)
    assert len(memories) == 1


@pytest.mark.integration
def test_persistence_service_save_turn(persistence):
    """Test atomic save_turn."""
    session = persistence.start_session("Manya")
    
    user_msg_id, asst_msg_id, mem_id = persistence.save_turn(
        user_content="I like pizza",
        assistant_content="That's great!",
        language="english",
        user_emotion="happy",
        confidence=0.8,
        memory_note="User preference: I like pizza"
    )
    
    assert user_msg_id is not None
    assert asst_msg_id is not None
    assert mem_id is not None
    
    # Verify messages saved
    messages = persistence.get_history()
    assert len(messages) == 1
    assert messages[0]["user"] == "I like pizza"
    assert messages[0]["assistant"] == "That's great!"
    
    # Verify memory saved
    memory_text = persistence.get_memory_text()
    assert "preference: I like pizza" in memory_text


@pytest.mark.integration
def test_persistence_service_get_history(persistence):
    """Test getting conversation history."""
    session = persistence.start_session("Manya")
    
    # Save a few turns
    persistence.save_turn("Hello", "Hi there!", "english")
    persistence.save_turn("How are you?", "I'm doing well!", "english")
    
    history = persistence.get_history()
    assert len(history) == 2
    assert history[0]["user"] == "Hello"
    assert history[1]["user"] == "How are you?"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])