"""Qdrant collection definitions and initialization."""
import logging
from qdrant_client.http import models
from voka.rag.qdrant_client import qdrant_manager
from voka.rag.embeddings import get_embedding_dimension

logger = logging.getLogger(__name__)

COLLECTION_MEMORIES = "voka_memories"
COLLECTION_KNOWLEDGE = "voka_knowledge"


def init_collections() -> None:
    """Create collections if they don't exist. Validate dimensions."""
    client = qdrant_manager.get_client()
    dim = get_embedding_dimension()

    # Personal Memories Collection
    if not client.collection_exists(COLLECTION_MEMORIES):
        client.create_collection(
            collection_name=COLLECTION_MEMORIES,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )
        # Payload indexes for filtering
        client.create_payload_index(COLLECTION_MEMORIES, "user_id", models.PayloadSchemaType.KEYWORD)
        client.create_payload_index(COLLECTION_MEMORIES, "character_id", models.PayloadSchemaType.KEYWORD)
        client.create_payload_index(COLLECTION_MEMORIES, "memory_type", models.PayloadSchemaType.KEYWORD)
        logger.info(f"Created collection: {COLLECTION_MEMORIES}")

    # Knowledge Documents Collection
    if not client.collection_exists(COLLECTION_KNOWLEDGE):
        client.create_collection(
            collection_name=COLLECTION_KNOWLEDGE,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )
        client.create_payload_index(COLLECTION_KNOWLEDGE, "document_id", models.PayloadSchemaType.KEYWORD)
        client.create_payload_index(COLLECTION_KNOWLEDGE, "category", models.PayloadSchemaType.KEYWORD)
        client.create_payload_index(COLLECTION_KNOWLEDGE, "language", models.PayloadSchemaType.KEYWORD)
        logger.info(f"Created collection: {COLLECTION_KNOWLEDGE}")

    # Validate existing collections
    for name in [COLLECTION_MEMORIES, COLLECTION_KNOWLEDGE]:
        info = client.get_collection(name)
        if info.config.params.vectors.size != dim:
            raise ValueError(f"Collection {name} has dimension {info.config.params.vectors.size}, expected {dim}")


def delete_collections() -> None:
    """Development utility: drop all VOKA collections."""
    client = qdrant_manager.get_client()
    for name in [COLLECTION_MEMORIES, COLLECTION_KNOWLEDGE]:
        if client.collection_exists(name):
            client.delete_collection(name)
            logger.info(f"Deleted collection: {name}")