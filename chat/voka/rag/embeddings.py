"""Embedding service using Sentence Transformers with fallback support."""
import logging
import os
import torch
from sentence_transformers import SentenceTransformer
from voka.config.settings import EMBEDDING_MODEL, EMBEDDING_DEVICE

logger = logging.getLogger(__name__)

_model = None
_model_name = None
_device = None

# Fallback models in order of preference
FALLBACK_MODELS = [
    "BAAI/bge-m3",           # 1024-dim, multilingual, best quality
    "sentence-transformers/all-MiniLM-L6-v2",  # 384-dim, fast, reliable
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # 384-dim, multilingual
]


def _get_device() -> str:
    """Resolve device preference."""
    if EMBEDDING_DEVICE != "auto":
        return EMBEDDING_DEVICE
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _try_load_model(model_name: str, device: str) -> SentenceTransformer | None:
    """Try to load a specific model, return None on failure."""
    try:
        logger.info(f"Attempting to load embedding model: {model_name} on {device}")
        return SentenceTransformer(model_name, device=device)
    except Exception as e:
        logger.warning(f"Failed to load {model_name}: {e}")
        return None


def get_model() -> SentenceTransformer:
    """Load model once, reuse across calls. Try preferred model, fallback on failure."""
    global _model, _model_name, _device

    device = _get_device()

    # If already loaded with correct config, return it
    if _model is not None and _model_name == EMBEDDING_MODEL and _device == device:
        return _model

    # Try preferred model first
    preferred = EMBEDDING_MODEL
    if preferred not in FALLBACK_MODELS:
        FALLBACK_MODELS.insert(0, preferred)

    for model_name in FALLBACK_MODELS:
        model = _try_load_model(model_name, device)
        if model is not None:
            _model = model
            _model_name = model_name
            _device = device
            logger.info(f"Successfully loaded embedding model: {model_name} (dim={model.get_sentence_embedding_dimension()})")
            return _model

    raise RuntimeError("Failed to load any embedding model")


def get_embedding_dimension() -> int:
    """Return the embedding dimension for the loaded model."""
    return get_model().get_sentence_embedding_dimension()


def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    if not text or not text.strip():
        return [0.0] * get_embedding_dimension()
    model = get_model()
    vec = model.encode(text.strip(), normalize_embeddings=True)
    return vec.tolist()


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed multiple documents in batch."""
    if not texts:
        return []
    model = get_model()
    # Filter empty strings but keep indices
    valid = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
    if not valid:
        return [[0.0] * get_embedding_dimension()] * len(texts)

    indices, valid_texts = zip(*valid)
    vectors = model.encode(list(valid_texts), normalize_embeddings=True, batch_size=32)

    # Reconstruct full list with zero vectors for empty inputs
    dim = get_embedding_dimension()
    result = [[0.0] * dim for _ in texts]
    for idx, vec in zip(indices, vectors):
        result[idx] = vec.tolist()
    return result