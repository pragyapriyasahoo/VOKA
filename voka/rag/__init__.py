"""VOKA RAG (Retrieval-Augmented Generation) module.

This module uses lazy imports to avoid loading the embedding model at import time.
"""

# Re-export from submodules (lazy imports)
from voka.rag.embeddings import embed_query, embed_documents, get_embedding_dimension
from voka.rag.qdrant_client import qdrant_manager
from voka.rag.collections import init_collections, COLLECTION_MEMORIES, COLLECTION_KNOWLEDGE
from voka.rag.vector_store import (
    upsert_memory_vector,
    delete_memory_vector,
    search_memories,
    upsert_document_chunks,
    delete_document_vectors,
    search_knowledge,
)
from voka.rag.document_loader import extract_text
from voka.rag.chunker import chunk_text, Chunk
from voka.rag.ingest import ingest_document, delete_document, reingest_document, IngestionResult
from voka.rag.retriever import retrieve_relevant_memories, format_memories_for_prompt
from voka.rag.query import retrieve_knowledge, format_knowledge_for_prompt
from voka.rag.context import build_rag_context, merge_context

__all__ = [
    # Embeddings
    "embed_query",
    "embed_documents",
    "get_embedding_dimension",
    # Qdrant
    "qdrant_manager",
    "init_collections",
    "COLLECTION_MEMORIES",
    "COLLECTION_KNOWLEDGE",
    # Vector operations
    "upsert_memory_vector",
    "delete_memory_vector",
    "search_memories",
    "upsert_document_chunks",
    "delete_document_vectors",
    "search_knowledge",
    # Document processing
    "extract_text",
    "chunk_text",
    "Chunk",
    # Ingestion
    "ingest_document",
    "delete_document",
    "reingest_document",
    "IngestionResult",
    # Retrieval
    "retrieve_relevant_memories",
    "format_memories_for_prompt",
    "retrieve_knowledge",
    "format_knowledge_for_prompt",
    # Context building
    "build_rag_context",
    "merge_context",
]