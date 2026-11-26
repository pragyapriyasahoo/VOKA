"""Vector database operations - Qdrant implementation."""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from qdrant_client.http import models

from voka.rag.qdrant_client import qdrant_manager
from voka.rag.collections import COLLECTION_MEMORIES, COLLECTION_KNOWLEDGE
from voka.rag.embeddings import embed_query, embed_documents

logger = logging.getLogger(__name__)


def _search(client, collection_name: str, vector: list[float], query_filter, limit: int, score_threshold: float):
    """Search using the new query_points API (Qdrant client >= 1.8)."""
    return client.query_points(
        collection_name=collection_name,
        query=vector,
        query_filter=query_filter,
        limit=limit,
        score_threshold=score_threshold,
        with_payload=True,
    ).points


# ---------- Personal Memories ----------

def upsert_memory_vector(
    memory_id: uuid.UUID,
    user_id: uuid.UUID,
    character_id: uuid.UUID,
    memory_type: str,
    content: str,
    importance: float = 1.0,
    source_message_id: Optional[uuid.UUID] = None,
) -> bool:
    """Upsert a memory vector to Qdrant. Returns success."""
    try:
        client = qdrant_manager.get_client()
        vector = embed_query(content)

        point = models.PointStruct(
            id=str(memory_id),
            vector=vector,
            payload={
                "user_id": str(user_id),
                "character_id": str(character_id),
                "memory_type": memory_type,
                "content": content,
                "importance": importance,
                "source_message_id": str(source_message_id) if source_message_id else None,
            },
        )
        client.upsert(collection_name=COLLECTION_MEMORIES, points=[point])
        return True
    except Exception as e:
        logger.error(f"Failed to upsert memory vector {memory_id}: {e}")
        return False


def delete_memory_vector(memory_id: uuid.UUID) -> bool:
    """Delete a memory vector from Qdrant."""
    try:
        client = qdrant_manager.get_client()
        client.delete(
            collection_name=COLLECTION_MEMORIES,
            points_selector=models.PointIdsList(points=[str(memory_id)]),
        )
        return True
    except Exception as e:
        logger.error(f"Failed to delete memory vector {memory_id}: {e}")
        return False


def search_memories(
    query: str,
    user_id: uuid.UUID,
    character_id: uuid.UUID,
    limit: int = 5,
    score_threshold: float = 0.7,
    memory_types: Optional[list[str]] = None,
) -> list[dict]:
    """Semantic search for relevant memories."""
    try:
        client = qdrant_manager.get_client()
        vector = embed_query(query)

        must = [
            models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
            models.FieldCondition(key="character_id", match=models.MatchValue(value=str(character_id))),
        ]
        if memory_types:
            must.append(models.FieldCondition(key="memory_type", match=models.MatchAny(any=memory_types)))

        results = _search(
            client,
            COLLECTION_MEMORIES,
            vector,
            models.Filter(must=must),
            limit,
            score_threshold,
        )
        return [{"id": r.id, "score": r.score, **r.payload} for r in results]
    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        return []


# ---------- Knowledge Documents ----------

def upsert_document_chunks(
    document_id: uuid.UUID,
    chunks: list[dict],  # Each: {chunk_id, content, metadata}
) -> bool:
    """Upsert document chunks to Qdrant."""
    try:
        client = qdrant_manager.get_client()
        texts = [c["content"] for c in chunks]
        vectors = embed_documents(texts)

        points = []
        for chunk, vector in zip(chunks, vectors):
            payload = {
                "document_id": str(document_id),
                "chunk_id": str(chunk["chunk_id"]),
                "content": chunk["content"],
                **chunk.get("metadata", {}),
            }
            points.append(models.PointStruct(id=str(chunk["chunk_id"]), vector=vector, payload=payload))

        client.upsert(collection_name=COLLECTION_KNOWLEDGE, points=points)
        return True
    except Exception as e:
        logger.error(f"Failed to upsert document chunks for {document_id}: {e}")
        return False


def delete_document_vectors(document_id: uuid.UUID) -> bool:
    """Delete all chunks for a document."""
    try:
        client = qdrant_manager.get_client()
        client.delete(
            collection_name=COLLECTION_KNOWLEDGE,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=str(document_id)))]
                )
            ),
        )
        return True
    except Exception as e:
        logger.error(f"Failed to delete document vectors for {document_id}: {e}")
        return False


def search_knowledge(
    query: str,
    limit: int = 5,
    score_threshold: float = 0.6,
    category: Optional[str] = None,
    language: Optional[str] = None,
    document_ids: Optional[list[uuid.UUID]] = None,
) -> list[dict]:
    """Semantic search for relevant knowledge chunks."""
    try:
        client = qdrant_manager.get_client()
        vector = embed_query(query)

        must = []
        if category:
            must.append(models.FieldCondition(key="category", match=models.MatchValue(value=category)))
        if language:
            must.append(models.FieldCondition(key="language", match=models.MatchValue(value=language)))
        if document_ids:
            must.append(models.FieldCondition(key="document_id", match=models.MatchAny(any=[str(d) for d in document_ids])))

        results = _search(
            client,
            COLLECTION_KNOWLEDGE,
            vector,
            models.Filter(must=must) if must else None,
            limit,
            score_threshold,
        )
        return [{"id": r.id, "score": r.score, **r.payload} for r in results]
    except Exception as e:
        logger.error(f"Knowledge search failed: {e}")
        return []