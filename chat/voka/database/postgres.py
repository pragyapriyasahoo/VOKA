from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from voka.config.settings import (
    DATABASE_URL,
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
)


class PostgresDatabase:
    """Small persistence adapter for Voka's structured PostgreSQL data."""

    def __init__(self, connection_url: str | None = None):
        self.connection_url = connection_url or DATABASE_URL
        self.connection = None

    def connect(self):
        import psycopg
        from psycopg.rows import dict_row

        if self.connection_url:
            self.connection = psycopg.connect(self.connection_url, row_factory=dict_row)
        else:
            kwargs = {
                "host": DB_HOST,
                "port": DB_PORT,
                "dbname": DB_NAME,
                "user": DB_USER,
                "row_factory": dict_row,
            }
            if DB_PASSWORD:
                kwargs["password"] = DB_PASSWORD
            self.connection = psycopg.connect(**kwargs)
        return self

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def _require_connection(self):
        if self.connection is None or self.connection.closed:
            raise RuntimeError("PostgreSQL is not connected.")
        return self.connection

    def create_schema(self):
        """Run all migrations to create/update schema."""
        from voka.database.migrations import run_migrations
        run_migrations(self.connection_url)

    def create_user(self, user_id: uuid.UUID | None = None) -> uuid.UUID:
        user_id = user_id or uuid.uuid4()
        with self._require_connection().cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (id) VALUES (%s) ON CONFLICT (id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP RETURNING id",
                (user_id,),
            )
            result = cursor.fetchone()["id"]
        self.connection.commit()
        return result

    def get_user(self, user_id: uuid.UUID):
        with self._require_connection().cursor() as cursor:
            cursor.execute("SELECT id, created_at, updated_at FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()

    def create_character(self, name: str) -> uuid.UUID:
        character_id = uuid.uuid5(uuid.NAMESPACE_URL, f"voka:character:{name}")
        with self._require_connection().cursor() as cursor:
            cursor.execute(
                "INSERT INTO characters (id, name) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
                (character_id, name),
            )
            result = cursor.fetchone()["id"]
        self.connection.commit()
        return result

    def create_conversation(self, user_id: uuid.UUID, character_id: uuid.UUID) -> uuid.UUID:
        conversation_id = uuid.uuid4()
        with self._require_connection().cursor() as cursor:
            cursor.execute(
                "INSERT INTO conversations (id, user_id, character_id) VALUES (%s, %s, %s)",
                (conversation_id, user_id, character_id),
            )
        self.connection.commit()
        return conversation_id

    def end_conversation(self, conversation_id: uuid.UUID) -> None:
        with self._require_connection().cursor() as cursor:
            cursor.execute("UPDATE conversations SET ended_at = CURRENT_TIMESTAMP WHERE id = %s", (conversation_id,))
        self.connection.commit()

    def save_message(self, conversation_id, role: str, content: str, language: str | None = None,
                     emotion: str | None = None, emotion_confidence: float | None = None):
        message_id = uuid.uuid4()
        connection = self._require_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO messages
                    (id, conversation_id, role, content, language, emotion, emotion_confidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (message_id, conversation_id, role, content, language, emotion, emotion_confidence),
                )
                if role == "user" and emotion:
                    cursor.execute(
                        "INSERT INTO emotion_events (id, message_id, emotion, confidence) VALUES (%s, %s, %s, %s)",
                        (uuid.uuid4(), message_id, emotion, emotion_confidence),
                    )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return message_id

    def save_turn(self, conversation_id: uuid.UUID, user_content: str, assistant_content: str,
                  language: str, user_emotion: str | None = None, 
                  emotion_confidence: float | None = None,
                  memory_note: str | None = None,
                  user_id: uuid.UUID | None = None,
                  character_id: uuid.UUID | None = None) -> tuple:
        """
        Atomically save a complete conversation turn:
        - User message with emotion
        - Assistant message
        - Memory (if provided)
        
        All in a single transaction.
        
        Returns:
            tuple: (user_message_id, assistant_message_id, memory_id or None)
        """
        user_message_id = uuid.uuid4()
        assistant_message_id = uuid.uuid4()
        memory_id = None
        
        connection = self._require_connection()
        try:
            with connection.cursor() as cursor:
                # 1. Insert user message
                cursor.execute(
                    """INSERT INTO messages
                    (id, conversation_id, role, content, language, emotion, emotion_confidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (user_message_id, conversation_id, "user", user_content, language, user_emotion, emotion_confidence),
                )
                
                # 2. Insert emotion event for user message
                if user_emotion:
                    cursor.execute(
                        "INSERT INTO emotion_events (id, message_id, emotion, confidence) VALUES (%s, %s, %s, %s)",
                        (uuid.uuid4(), user_message_id, user_emotion, emotion_confidence),
                    )
                
                # 3. Insert assistant message
                cursor.execute(
                    """INSERT INTO messages
                    (id, conversation_id, role, content, language)
                    VALUES (%s, %s, %s, %s, %s)""",
                    (assistant_message_id, conversation_id, "assistant", assistant_content, language),
                )
                
                # 4. Insert memory if provided
                if memory_note and user_id and character_id:
                    memory_id = uuid.uuid4()
                    if memory_note.startswith("User emotion:"):
                        memory_type = "emotion_context"
                    elif memory_note.startswith("User fact:"):
                        memory_type = "fact"
                    else:
                        memory_type = "preference"
                    content = memory_note.split(":", 1)[1].strip() if ":" in memory_note else memory_note
                    cursor.execute(
                        """INSERT INTO memories
                        (id, user_id, character_id, memory_type, content, importance, source_message_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, character_id, content) DO NOTHING
                        RETURNING id""",
                        (memory_id, user_id, character_id, memory_type, content, 1.0, user_message_id),
                    )
                    # If conflict, memory_id will be None from fetchone
                    result = cursor.fetchone()
                    if result is None:
                        memory_id = None
                
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        
        return (user_message_id, assistant_message_id, memory_id)

    def get_recent_messages(self, conversation_id, limit: int = 6):
        with self._require_connection().cursor() as cursor:
            cursor.execute(
                """SELECT role, content, language, emotion, created_at
                FROM messages WHERE conversation_id = %s
                ORDER BY created_at, 
                    CASE role WHEN 'user' THEN 0 WHEN 'assistant' THEN 1 ELSE 2 END ASC
                LIMIT %s""",
                (conversation_id, limit),
            )
            return list(cursor.fetchall())

    def save_memory(self, user_id, character_id, memory_type: str, content: str,
                    source_message_id=None, importance: float = 1.0):
        memory_id = uuid.uuid4()
        with self._require_connection().cursor() as cursor:
            cursor.execute(
                """INSERT INTO memories
                (id, user_id, character_id, memory_type, content, importance, source_message_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, character_id, content) DO NOTHING
                RETURNING id""",
                (memory_id, user_id, character_id, memory_type, content, importance, source_message_id),
            )
            result = cursor.fetchone()
            if result is None:
                return None
            return result["id"]

    def get_memories(self, user_id, character_id, limit: int = 20):
        with self._require_connection().cursor() as cursor:
            cursor.execute(
                """SELECT memory_type, content, importance, source_message_id, updated_at
                FROM memories WHERE user_id = %s AND character_id = %s
                ORDER BY updated_at DESC LIMIT %s""",
                (user_id, character_id, limit),
            )
            return list(cursor.fetchall())

    def save_emotion_event(self, message_id, emotion: str, confidence: float | None = None):
        with self._require_connection().cursor() as cursor:
            cursor.execute(
                "INSERT INTO emotion_events (id, message_id, emotion, confidence) VALUES (%s, %s, %s, %s)",
                (uuid.uuid4(), message_id, emotion, confidence or 0.0),
            )
        self.connection.commit()

    def delete_memory(self, memory_id: uuid.UUID) -> bool:
        with self._require_connection().cursor() as cursor:
            cursor.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
            deleted = cursor.rowcount > 0
        self.connection.commit()
        return deleted