"""Knowledge base retrieval."""
import uuid
from typing import Optional

from voka.rag.vector_store import search_knowledge
from voka.config.settings import KNOWLEDGE_TOP_K, KNOWLEDGE_SCORE_THRESHOLD


def retrieve_knowledge(
    query: str,
    limit: int = None,
    score_threshold: float = None,
    category: Optional[str] = None,
    language: Optional[str] = None,
    document_ids: Optional[list[uuid.UUID]] = None,
) -> list[dict]:
    """Retrieve relevant knowledge chunks."""
    limit = limit or KNOWLEDGE_TOP_K
    threshold = score_threshold if score_threshold is not None else KNOWLEDGE_SCORE_THRESHOLD

    return search_knowledge(
        query=query,
        limit=limit,
        score_threshold=threshold,
        category=category,
        language=language,
        document_ids=document_ids,
    )


def format_knowledge_for_prompt(chunks: list[dict]) -> str:
    """Format retrieved knowledge for prompt injection with source attribution."""
    if not chunks:
        return "No relevant knowledge found."

    lines = []
    for c in chunks:
        source = c.get("source_filename", "unknown")
        page = c.get("page", "")
        category = c.get("category", "general")
        content = c.get("content", "")
        score = c.get("score", 0)

        ref = f"[{category}]"
        if page:
            ref += f" {source}:{page}"
        else:
            ref += f" {source}"
        ref += f" (relevance: {score:.2f})"
        lines.append(f"{ref}\n{content}")
    return "\n\n---\n\n".join(lines)