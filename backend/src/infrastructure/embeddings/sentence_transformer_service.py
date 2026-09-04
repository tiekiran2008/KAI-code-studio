from typing import List
from sentence_transformers import SentenceTransformer
from src.domain.interfaces.embedding import IEmbeddingService

class SentenceTransformerService(IEmbeddingService):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Automatically downloads and caches the model. Runs on CPU.
        self.model = SentenceTransformer(model_name)
        
    def generate_embedding(self, text: str) -> List[float]:
        return self.model.encode(text).tolist()

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts).tolist()
        
    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()
