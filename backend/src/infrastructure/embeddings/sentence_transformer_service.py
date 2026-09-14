import os
import threading
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from src.domain.interfaces.embedding import IEmbeddingService
from src.core.logger import logger


class SentenceTransformerService(IEmbeddingService):
    """
    SentenceTransformer embedding service.
    Uses a process-level thread-safe singleton model cache to prevent repeated
    model initializations across requests and background tasks.
    """
    _model_lock = threading.Lock()
    _shared_model: Optional[SentenceTransformer] = None
    _shared_dimension: int = 384

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._ensure_model_loaded()

    def _ensure_model_loaded(self) -> None:
        if SentenceTransformerService._shared_model is not None:
            return

        with SentenceTransformerService._model_lock:
            if SentenceTransformerService._shared_model is not None:
                return

            logger.info("sentence_transformer_init_start", model=self.model_name)
            # Try loading locally first to avoid unnecessary remote Hugging Face checks
            try:
                model = SentenceTransformer(self.model_name, local_files_only=True)
            except Exception:
                # If local load fails, download and cache the model
                model = SentenceTransformer(self.model_name)

            SentenceTransformerService._shared_model = model
            try:
                if hasattr(model, "get_embedding_dimension"):
                    dim = model.get_embedding_dimension()
                else:
                    dim = model.get_sentence_embedding_dimension()
                SentenceTransformerService._shared_dimension = int(dim)
            except Exception:
                SentenceTransformerService._shared_dimension = 384

            logger.info(
                "sentence_transformer_init_complete",
                model=self.model_name,
                dimension=SentenceTransformerService._shared_dimension,
            )

    @property
    def model(self) -> SentenceTransformer:
        if SentenceTransformerService._shared_model is None:
            self._ensure_model_loaded()
        return SentenceTransformerService._shared_model

    def generate_embedding(self, text: str) -> List[float]:
        return self.model.encode(text).tolist()

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return self.model.encode(texts).tolist()

    @property
    def dimension(self) -> int:
        return SentenceTransformerService._shared_dimension

