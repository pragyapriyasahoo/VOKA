"""Build combined RAG context for LLM prompt."""
import uuid
from typing import Optional

from voka.rag.retriever import retrieve_relevant_memories, format_memories_for_prompt
from voka.rag.query import retrieve_knowledge, format_knowledge_for_prompt


def build_rag_context(
    query: str,
    user_id: uuid.UUID,
    character_id: uuid.UUID,
    include_memories: bool = True,
    include_knowledge: bool = True,
) -> dict:
    """
    Retrieve and format both personal memories and knowledge.
    Returns dict with formatted strings and raw results.
    """
    memories = []
    knowledge = []

    if include_memories:
        memories = retrieve_relevant_memories(query, user_id, character_id)

    if include_knowledge:
        knowledge = retrieve_knowledge(query)

    return {
        "memories_raw": memories,
        "knowledge_raw": knowledge,
        "memories_formatted": format_memories_for_prompt(memories),
        "knowledge_formatted": format_knowledge_for_prompt(knowledge),
        "has_context": bool(memories or knowledge),
    }


def merge_context(
    system_prompt: str,
    history: list[dict],
    user_input: str,
    emotion: str,
    rag_context: dict,
    long_memory: str = "",
) -> str:
    """
    Merge RAG context with existing prompt builder logic.
    This will be called from voka/app.py instead of direct build_prompt().
    """
    from voka.llm.prompts import build_prompt as original_build_prompt

    # Combine long_memory (legacy) with RAG memories
    combined_memory = long_memory
    if rag_context["memories_formatted"] != "No relevant memories found.":
        if combined_memory:
            combined_memory += "\n\n" + rag_context["memories_formatted"]
        else:
            combined_memory = rag_context["memories_formatted"]

    # Add knowledge as separate section
    knowledge_section = ""
    if rag_context["knowledge_formatted"] != "No relevant knowledge found.":
        knowledge_section = (
            f"\n\n<KNOWLEDGE_BASE>\n{rag_context['knowledge_formatted']}\n</KNOWLEDGE_BASE>\n\n"
            "KNOWLEDGE RULE:\n"
            "Use the knowledge base only when relevant to the user's question. "
            "Cite sources when using information from it. "
            "Do not hallucinate beyond what is provided."
        )

    # Build base prompt
    prompt = original_build_prompt(system_prompt, history, combined_memory, user_input, emotion)

    # Inject knowledge section before the final USER/ASSISTANT delimiter
    if knowledge_section:
        prompt = prompt.replace("USER:\n", knowledge_section + "\nUSER:\n")

    return prompt