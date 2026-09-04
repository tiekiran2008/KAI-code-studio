from abc import ABC, abstractmethod
from typing import List, Dict, Any
from src.domain.models.chunk import SemanticChunk

class IVectorDB(ABC):
    @abstractmethod
    def upsert_chunks(self, collection_name: str, chunks: List[SemanticChunk], embeddings: List[List[float]]):
        pass

    @abstractmethod
    def delete_by_file(self, collection_name: str, repo_id: str, file_path: str):
        pass

    @abstractmethod
    def delete_by_repo(self, collection_name: str, repo_id: str):
        pass

    @abstractmethod
    def search(self, collection_name: str, query_embedding: List[float], filter_metadata: Dict[str, Any] = None, limit: int = 10) -> List[Dict[str, Any]]:
        pass

