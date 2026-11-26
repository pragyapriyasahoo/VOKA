"""Text chunking with overlap for document ingestion."""
import re
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class Chunk:
    chunk_id: uuid.UUID
    content: str
    metadata: dict


def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    document_id: uuid.UUID = None,
    source_filename: str = "",
    category: str = "general",
    language: str = "english",
) -> list[Chunk]:
    """Split text into overlapping chunks with metadata."""
    if not text or not text.strip():
        return []

    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    chunks = []
    start = 0
    chunk_index = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        # Try to break at sentence boundary
        if end < text_len:
            # Look for sentence end within last 100 chars
            search_start = max(start + chunk_size - 100, start)
            sentence_end = text.rfind('.', search_start, end)
            if sentence_end != -1:
                end = sentence_end + 1

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunk_id = uuid.uuid4()
            metadata = {
                "document_id": str(document_id) if document_id else None,
                "chunk_index": chunk_index,
                "source_filename": source_filename,
                "category": category,
                "language": language,
                "char_start": start,
                "char_end": end,
            }
            chunks.append(Chunk(chunk_id=chunk_id, content=chunk_text, metadata=metadata))
            chunk_index += 1

        # Move start position - ensure we make progress
        if end == text_len:
            # Reached end of text
            break
        start = end - chunk_overlap
        if start >= text_len:
            break

    return chunks