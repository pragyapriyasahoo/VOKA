"""Semantic retrieval for personal memories."""
import logging
import uuid
from typing import Optional

from voka.rag.vector_store import search_memories
from voka.config.settings import MEMORY_TOP_K, MEMORY_SCORE_THRESHOLD

logger = logging.getLogger(__name__)


def retrieve_relevant_memories(
    query: str,
    user_id: uuid.UUID,
    character_id: uuid.UUID,
    limit: int = None,
    score_threshold: float = None,
    memory_types: Optional[list[str]] = None,
) -> list[dict]:
    """
    Retrieve semantically relevant memories for the current user/character.
    Returns list of memory dicts with score and metadata.
    """
    limit = limit or MEMORY_TOP_K
    threshold = score_threshold if score_threshold is not None else MEMORY_SCORE_THRESHOLD

    results = search_memories(
        query=query,
        user_id=user_id,
        character_id=character_id,
        limit=limit,
        score_threshold=threshold,
        memory_types=memory_types,
    )

    return results


def format_memories_for_prompt(memories: list[dict]) -> str:
    """Format retrieved memories for prompt injection."""
    if not memories:
        return "No relevant memories found."

    lines = []
    for m in memories:
        mtype = m.get("memory_type", "unknown")
        content = m.get("content", "")
        score = m.get("score", 0)
        lines.append(f"[{mtype}] (relevance: {score:.2f}) {content}")
    return "\n".join(lines)