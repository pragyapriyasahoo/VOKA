"""Qdrant connection management with health checks and retry logic."""
import logging
from qdrant_client import QdrantClient
from voka.config.settings import QDRANT_URL, QDRANT_API_KEY

logger = logging.getLogger(__name__)


class QdrantManager:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        return self._client

    def health_check(self) -> bool:
        try:
            self.get_client().get_collections()
            return True
        except Exception as e:
            logger.warning(f"Qdrant health check failed: {e}")
            return False

    def close(self):
        if self._client:
            self._client.close()
            self._client = None


qdrant_manager = QdrantManager()