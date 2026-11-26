from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
MEMORY_DIR = BASE_DIR.parent / "memory"
EMOTION_MODEL_DIR = BASE_DIR.parent / "emotion_model"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "gemma3"
MAX_TURNS = 6
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
load_dotenv(BASE_DIR.parent / ".env")

# PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_HOST = os.getenv("VOKA_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("VOKA_DB_PORT", "5432"))
DB_NAME = os.getenv("VOKA_DB_NAME", "voka")
DB_USER = os.getenv("VOKA_DB_USER", "postgres")
DB_PASSWORD = os.getenv("VOKA_DB_PASSWORD", "")

# Qdrant
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)

# Embedding model
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "auto")  # auto, cpu, cuda, mps

# Retrieval settings
MEMORY_TOP_K = int(os.getenv("MEMORY_TOP_K", "5"))
KNOWLEDGE_TOP_K = int(os.getenv("KNOWLEDGE_TOP_K", "5"))
MEMORY_SCORE_THRESHOLD = float(os.getenv("MEMORY_SCORE_THRESHOLD", "0.7"))
KNOWLEDGE_SCORE_THRESHOLD = float(os.getenv("KNOWLEDGE_SCORE_THRESHOLD", "0.6"))

# Document ingestion
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "512"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "50"))