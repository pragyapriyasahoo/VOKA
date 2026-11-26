"""RAG system tests."""
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock, AsyncMock

import pytest


# Chunker (no embeddings needed)
def test_chunker_basic():
    from voka.rag.chunker import chunk_text
    text = "This is sentence one. This is sentence two. This is sentence three."
    chunks = chunk_text(text, chunk_size=50, chunk_overlap=10)
    assert len(chunks) >= 1
    assert all(c.content for c in chunks)


def test_chunker_empty():
    from voka.rag.chunker import chunk_text
    assert chunk_text("") == []
    assert chunk_text("   ") == []


# Document Loader (no embeddings needed)
def test_document_loader_txt():
    from voka.rag.document_loader import extract_text
    with TemporaryDirectory() as d:
        p = Path(d) / "test.txt"
        p.write_text("Hello world\nLine 2")
        text = extract_text(p)
        assert "Hello world" in text


# Memory RAG Integration - mock Qdrant at the right level
@patch("voka.rag.vector_store.qdrant_manager")
def test_memory_indexing_on_save(mock_qdrant_manager):
    from voka.database.repositories import PersistenceService
    from voka.database.postgres import PostgresDatabase
    
    # Mock Qdrant client
    mock_client = MagicMock()
    mock_qdrant_manager.get_client.return_value = mock_client
    
    # Mock PostgreSQL
    mock_db = MagicMock(spec=PostgresDatabase)
    mock_db.save_memory.return_value = uuid.uuid4()
    
    service = PersistenceService(database=mock_db, require_postgres=False)
    service.using_postgres = True
    service.database = mock_db
    service.start_session("Manya")
    
    mem_id = service.save_memory("User preference: I like tea", uuid.uuid4())
    
    assert mem_id is not None
    mock_client.upsert.assert_called_once()


# Knowledge Ingestion - mock Qdrant and Postgres
@patch("voka.rag.vector_store.qdrant_manager")
@patch("voka.rag.ingest.PostgresDatabase")
def test_document_ingestion(mock_pg_class, mock_qdrant_manager):
    from voka.rag.ingest import ingest_document
    
    # Mock Qdrant client
    mock_client = MagicMock()
    mock_qdrant_manager.get_client.return_value = mock_client
    
    # Mock PostgreSQL
    mock_pg = MagicMock()
    mock_pg_class.return_value = mock_pg
    mock_cursor = MagicMock()
    mock_pg._require_connection.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    
    with TemporaryDirectory() as d:
        p = Path(d) / "test.txt"
        p.write_text("This is a test document about mental health. " * 20)
        
        result = ingest_document(p, category="mental_health")
        
        assert result.success
        assert result.chunks_ingested > 0
        mock_client.upsert.assert_called_once()
        mock_pg.connect.assert_called()
        mock_pg.close.assert_called()


# Application Integration - mock embeddings and Qdrant
@patch("voka.app.build_rag_context")
@patch("voka.app.generate_response", return_value="Test response")
@patch("voka.app.predict_emotion", return_value="happy")
@patch("voka.app.detect_safety_trigger", return_value=None)
@patch("voka.app.extract_memory", return_value=None)
def test_respond_uses_rag_context(mock_extract, mock_safety, mock_emotion, mock_ollama, mock_rag):
    from voka.app import respond
    from voka.database.repositories import PersistenceService
    
    mock_rag.return_value = {
        "memories_raw": [],
        "knowledge_raw": [],
        "memories_formatted": "No relevant memories found.",
        "knowledge_formatted": "No relevant knowledge found.",
        "has_context": False,
    }
    
    # Create a real service with mocked database
    mock_db = MagicMock()
    mock_db.get_recent_messages.return_value = []
    mock_db.get_memories.return_value = []
    mock_db.save_message.return_value = uuid.uuid4()
    mock_db.save_memory.return_value = uuid.uuid4()
    
    service = PersistenceService(database=mock_db, require_postgres=False)
    service.using_postgres = True
    service.database = mock_db
    service.start_session("Manya")
    
    with patch("voka.app.get_persistence", return_value=service):
        reply = respond("Manya", "How are you?")
        assert reply == "Test response"
        mock_rag.assert_called_once()