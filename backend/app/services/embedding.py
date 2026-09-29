"""Lazy, reusable Sentence Transformer embedding service."""

from threading import Lock
from typing import Any

from sentence_transformers import SentenceTransformer

from app.core.config import settings


class EmbeddingModelError(RuntimeError):
    pass


class EmbeddingService:
    """Load one model per service and generate normalized batch embeddings."""

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL, model: Any = None) -> None:
        self.model_name = model_name
        self._model = model
        self._lock = Lock()

    @property
    def model(self) -> Any:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        self._model = SentenceTransformer(self.model_name)
                    except Exception as exc:
                        raise EmbeddingModelError(
                            f"Embedding model '{self.model_name}' could not be loaded"
                        ) from exc
        return self._model

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in vectors]

    def embed_query(self, query: str) -> list[float]:
        if not query.strip():
            raise ValueError("Query must not be blank")
        return self.embed_texts([query], batch_size=1)[0]


embedding_service = EmbeddingService()
