from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

from voka.config.characters import CHARACTERS
from voka.database.postgres import PostgresDatabase
from voka.rag.vector_store import upsert_memory_vector, delete_memory_vector
from voka.memory import manager as local_memory

logger = logging.getLogger(__name__)
LOCAL_USER_ID = uuid.uuid5(uuid.NAMESPACE_URL, "voka:default-local-user")


@dataclass
class LocalSession:
    user_id: uuid.UUID = LOCAL_USER_ID
    character_id: uuid.UUID = field(default_factory=uuid.uuid4)
    conversation_id: uuid.UUID = field(default_factory=uuid.uuid4)
    character: str = ""
    messages: list[dict] = field(default_factory=list)


class PersistenceService:
    """Application persistence boundary with PostgreSQL (required)."""

    def __init__(self, database: PostgresDatabase | None = None, require_postgres: bool = True):
        self.database = database
        self.session: LocalSession | None = None
        self.using_postgres = False
        self._require_postgres = require_postgres
        self._ensure_database()

    def _ensure_database(self):
        if self.database is None:
            self.database = PostgresDatabase()
        try:
            self.database.connect()
            self.database.create_schema()
            for name in CHARACTERS:
                self.database.create_character(name)
            self.database.create_user(LOCAL_USER_ID)
            self.using_postgres = True
            logger.info("PostgreSQL connected and schema ready")
        except Exception as error:
            self.using_postgres = False
            try:
                self.database.close()
            except Exception:
                pass
            msg = f"PostgreSQL unavailable: {error}"
            if self._require_postgres:
                raise RuntimeError(msg) from error
            logger.warning("%s; using local fallback (DEPRECATED)", msg)

    def start_session(self, character: str):
        if self.using_postgres:
            user_id = self.database.create_user(LOCAL_USER_ID)
            character_id = self.database.create_character(character)
            conversation_id = self.database.create_conversation(user_id, character_id)
            self.session = LocalSession(user_id, character_id, conversation_id, character)
        else:
            self.session = LocalSession(character=character)
        return self.session

    def close(self):
        if self.session and self.using_postgres:
            self.database.end_conversation(self.session.conversation_id)
        if self.database:
            self.database.close()

    def save_user_message(self, content: str, language: str, emotion: str | None = None, confidence: float | None = None):
        session = self._require_session()
        if self.using_postgres:
            return self.database.save_message(
                session.conversation_id, "user", content, language, emotion, confidence
            )
        message_id = uuid.uuid4()
        session.messages.append({"role": "user", "content": content, "language": language, "emotion": emotion, "confidence": confidence, "id": message_id})
        return message_id

    def save_assistant_message(self, content: str, language: str):
        session = self._require_session()
        if self.using_postgres:
            return self.database.save_message(session.conversation_id, "assistant", content, language)
        message_id = uuid.uuid4()
        session.messages.append({"role": "assistant", "content": content, "language": language, "id": message_id})
        return message_id

    def save_turn(self, user_content: str, assistant_content: str, language: str,
                  user_emotion: str | None = None, confidence: float | None = None,
                  memory_note: str | None = None) -> tuple:
        """
        Atomically save a complete conversation turn.
        
        Returns:
            tuple: (user_message_id, assistant_message_id, memory_id or None)
        """
        session = self._require_session()
        if self.using_postgres:
            return self.database.save_turn(
                session.conversation_id,
                user_content,
                assistant_content,
                language,
                user_emotion,
                confidence,
                memory_note,
                session.user_id,
                session.character_id,
            )
        # Local fallback (deprecated)
        user_id = self.save_user_message(user_content, language, user_emotion, confidence)
        assistant_id = self.save_assistant_message(assistant_content, language)
        memory_id = None
        if memory_note:
            memory_id = self.save_memory(memory_note)
        return (user_id, assistant_id, memory_id)

    def save_crisis_turn(self, user_content: str, response: str, language: str):
        return self.save_turn(user_content, response, language)

    def save_memory(self, note: str, source_message_id=None):
        session = self._require_session()
        if note.startswith("User emotion:"):
            memory_type = "emotion_context"
        elif note.startswith("User fact:"):
            memory_type = "fact"
        else:
            memory_type = "preference"
        content = note.split(":", 1)[1].strip() if ":" in note else note
        if self.using_postgres:
            memory_id = self.database.save_memory(
                session.user_id,
                session.character_id,
                memory_type,
                content,
                source_message_id,
            )
            # NEW: Index in Qdrant (non-blocking, best-effort)
            if memory_id:
                try:
                    upsert_memory_vector(
                        memory_id=memory_id,
                        user_id=session.user_id,
                        character_id=session.character_id,
                        memory_type=memory_type,
                        content=content,
                        importance=1.0,
                        source_message_id=source_message_id,
                    )
                except Exception as e:
                    logger.warning(f"Qdrant indexing failed for memory {memory_id}: {e}")
            return memory_id
        local_memory.append_long_memory(session.character, note)
        return None

    def delete_memory(self, memory_id: uuid.UUID) -> bool:
        """Delete memory from PostgreSQL and Qdrant."""
        if self.using_postgres:
            success = self.database.delete_memory(memory_id)
            if success:
                try:
                    delete_memory_vector(memory_id)
                except Exception as e:
                    logger.warning(f"Qdrant deletion failed for memory {memory_id}: {e}")
            return success
        return False

    def get_history(self, exclude_latest: bool = False):
        session = self._require_session()
        if self.using_postgres:
            rows = self.database.get_recent_messages(session.conversation_id, limit=12)
            if exclude_latest and rows:
                rows = rows[:-1]
            return self._rows_to_turns(rows)
        rows = session.messages[:-1] if exclude_latest else session.messages
        return self._rows_to_turns(rows)

    def get_memory_text(self):
        session = self._require_session()
        if self.using_postgres:
            memories = self.database.get_memories(session.user_id, session.character_id)
            return "\n".join(f"{item['memory_type']}: {item['content']}" for item in memories)
        return local_memory.load_long_memory(session.character)

    def _rows_to_turns(self, rows):
        turns = []
        pending_user = None
        for row in rows:
            role = row["role"]
            content = row["content"]
            if role == "user":
                pending_user = content
            elif role == "assistant" and pending_user is not None:
                turns.append({"user": pending_user, "assistant": content})
                pending_user = None
        return turns

    def _require_session(self):
        if self.session is None:
            raise RuntimeError("No active Voka conversation.")
        return self.session