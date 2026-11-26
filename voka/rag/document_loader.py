"""Document text extraction for multiple formats."""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text(filepath: Path) -> Optional[str]:
    """Extract text from PDF, DOCX, TXT, or Markdown."""
    suffix = filepath.suffix.lower()

    try:
        if suffix == ".pdf":
            return _extract_pdf(filepath)
        elif suffix == ".docx":
            return _extract_docx(filepath)
        elif suffix in (".txt", ".md", ".markdown"):
            return filepath.read_text(encoding="utf-8")
        else:
            logger.warning(f"Unsupported file type: {suffix}")
            return None
    except Exception as e:
        logger.error(f"Failed to extract text from {filepath}: {e}")
        return None


def _extract_pdf(filepath: Path) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(filepath)
    text_parts = []
    for page_num, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            text_parts.append(f"[Page {page_num + 1}]\n{text}")
    doc.close()
    return "\n\n".join(text_parts)


def _extract_docx(filepath: Path) -> str:
    from docx import Document
    doc = Document(filepath)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())