"""Document ingestion pipeline for knowledge base."""
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from voka.rag.document_loader import extract_text
from voka.rag.chunker import chunk_text
from voka.rag.vector_store import upsert_document_chunks, delete_document_vectors
from voka.database.postgres import PostgresDatabase
from voka.config.settings import RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    document_id: uuid.UUID
    chunks_ingested: int
    success: bool
    error: str | None = None


def ingest_document(
    filepath: Path,
    category: str = "general",
    language: str = "english",
    document_id: uuid.UUID = None,
) -> IngestionResult:
    """Full ingestion pipeline: extract -> chunk -> embed -> store."""
    doc_id = document_id or uuid.uuid4()

    # 1. Extract text
    text = extract_text(filepath)
    if not text:
        return IngestionResult(doc_id, 0, False, "Text extraction failed")

    # 2. Chunk
    chunks = chunk_text(
        text=text,
        chunk_size=RAG_CHUNK_SIZE,
        chunk_overlap=RAG_CHUNK_OVERLAP,
        document_id=doc_id,
        source_filename=filepath.name,
        category=category,
        language=language,
    )
    if not chunks:
        return IngestionResult(doc_id, 0, False, "No valid chunks generated")

    # 3. Convert to dict format for vector store
    chunk_dicts = [
        {
            "chunk_id": c.chunk_id,
            "content": c.content,
            "metadata": c.metadata,
        }
        for c in chunks
    ]

    # 4. Upsert to Qdrant
    success = upsert_document_chunks(doc_id, chunk_dicts)
    if not success:
        return IngestionResult(doc_id, 0, False, "Qdrant upsert failed")

    # 5. Track in PostgreSQL
    _track_document_in_postgres(doc_id, filepath.name, category, language, len(chunks))

    logger.info(f"Ingested document {filepath.name} as {doc_id} ({len(chunks)} chunks)")
    return IngestionResult(doc_id, len(chunks), True)


def _track_document_in_postgres(doc_id, filename, category, language, chunk_count):
    """Record document metadata in PostgreSQL."""
    db = PostgresDatabase()
    try:
        db.connect()
        with db._require_connection().cursor() as cursor:
            cursor.execute(
                """INSERT INTO documents (id, filename, category, language, chunk_count)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    filename = EXCLUDED.filename,
                    category = EXCLUDED.category,
                    language = EXCLUDED.language,
                    chunk_count = EXCLUDED.chunk_count,
                    updated_at = CURRENT_TIMESTAMP""",
                (doc_id, filename, category, language, chunk_count),
            )
        db.connection.commit()
    finally:
        db.close()


def delete_document(document_id: uuid.UUID) -> bool:
    """Delete document from Qdrant and PostgreSQL."""
    from voka.database.postgres import PostgresDatabase

    # Delete from Qdrant
    qdrant_ok = delete_document_vectors(document_id)

    # Delete from PostgreSQL
    db = PostgresDatabase()
    try:
        db.connect()
        with db._require_connection().cursor() as cursor:
            cursor.execute("DELETE FROM documents WHERE id = %s", (document_id,))
        db.connection.commit()
        pg_ok = True
    except Exception as e:
        logger.error(f"PostgreSQL delete failed: {e}")
        pg_ok = False
    finally:
        db.close()

    return qdrant_ok and pg_ok


def reingest_document(document_id: uuid.UUID, filepath: Path) -> IngestionResult:
    """Re-ingest a document (delete old, ingest new)."""
    delete_document(document_id)
    return ingest_document(filepath, document_id=document_id)