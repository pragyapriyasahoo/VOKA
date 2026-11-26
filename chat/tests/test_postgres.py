import os
import uuid
from unittest.mock import MagicMock, Mock

from voka.database.postgres import PostgresDatabase


def configured_database():
    database = PostgresDatabase(os.getenv("DATABASE_URL", ""))
    try:
        database.connect()
        database.create_schema()
    except Exception as error:
        database.close()
        return None, str(error)
    return database, None


def test_database_integration():
    database, reason = configured_database()
    if database is None:
        print(f"SKIP PostgreSQL integration: {reason}")
        return
    try:
        user_id = database.create_user()
        assert database.get_user(user_id)["id"] == user_id
        character_id = database.create_character("Manya")
        conversation_id = database.create_conversation(user_id, character_id)
        message_id = database.save_message(conversation_id, "user", "I like tea", "english")
        database.save_emotion_event(message_id, "happy", 0.8)
        database.save_memory(user_id, character_id, "preference", "I like tea", message_id)
        database.save_message(conversation_id, "assistant", "That sounds nice.", "english")
        assert len(database.get_recent_messages(conversation_id)) == 2
        assert database.get_memories(user_id, character_id)[0]["content"] == "I like tea"
        try:
            database.save_message(uuid.uuid4(), "user", "invalid conversation")
        except Exception:
            pass
        else:
            raise AssertionError("Expected foreign-key integrity failure")
    finally:
        database.close()


def test_save_message_uses_parameters():
    database = PostgresDatabase()
    connection = MagicMock()
    connection.closed = 0
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = {"id": uuid.uuid4()}
    database.connection = connection
    conversation_id = uuid.uuid4()
    content = "'); DROP TABLE messages; --"
    database.save_message(conversation_id, "user", content)
    calls = cursor.execute.call_args_list
    assert any(call.args[1][3] == content for call in calls)
    assert "DROP TABLE" not in calls[0].args[0]


def test_database_unavailable_fallback_is_used():
    from voka.database.repositories import PersistenceService

    database = Mock()
    database.connect.side_effect = OSError("database unavailable")
    service = PersistenceService(database, require_postgres=False)
    assert service.using_postgres is False
    service.start_session("Manya")
    assert service.session.character == "Manya"
