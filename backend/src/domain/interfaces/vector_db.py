from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set
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

    @abstractmethod
    def get_indexed_files(self, collection_name: str, repo_id: str) -> Set[str]:
        """Return the set of distinct file_path values indexed for the given repo_id."""
        pass

    @abstractmethod
    def get_file_chunks(self, collection_name: str, repo_id: str, file_path: str) -> List[Dict[str, Any]]:
        """Return all chunk payloads stored for a specific file in the repository."""
        pass


