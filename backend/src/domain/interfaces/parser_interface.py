from abc import ABC, abstractmethod
from typing import List
from src.domain.models.repository import CodeSymbol

class IParser(ABC):
    @abstractmethod
    def parse_symbols(self, content: str, file_path: str) -> List[CodeSymbol]:
        """Parses the code content and returns a list of extracted symbols."""
        pass

    @abstractmethod
    def extract_imports(self, content: str) -> List[str]:
        """Extracts import dependencies from the code."""
        pass
