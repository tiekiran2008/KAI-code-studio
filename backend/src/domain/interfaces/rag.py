"""
RAG Pipeline Interfaces
=======================
Abstract contracts for every stage in the RAG pipeline.
Concrete implementations live in the application/rag/ package.
Following the Dependency Inversion Principle — high-level use cases
depend on these abstractions, not on concrete implementations.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.rag import (
    ParsedQuery,
    RerankedChunk,
    ContextWindow,
    RAGResponse,
    Citation,
    ValidationResult,
    ConversationHistory,
    EvaluationMetrics,
)
from src.domain.models.chunk import SearchResult


class IQueryUnderstanding(ABC):
    """Classifies user intent and extracts entities from raw query text."""

    @abstractmethod
    def classify_intent(self, query: str) -> "ParsedQuery":
        ...

    @abstractmethod
    def extract_symbols(self, query: str) -> List[str]:
        ...


class IQueryRewriter(ABC):
    """Expands and rewrites queries to improve retrieval recall."""

    @abstractmethod
    def rewrite(self, parsed_query: ParsedQuery) -> ParsedQuery:
        """Populates `parsed_query.rewritten_queries` in-place and returns it."""
        ...


class IRetriever(ABC):
    """Retrieves raw candidate chunks from the vector store."""

    @abstractmethod
    async def retrieve(
        self,
        parsed_query: ParsedQuery,
        limit: int = 20,
    ) -> List[SearchResult]:
        ...


class IReRanker(ABC):
    """Scores and sorts retrieved chunks using multiple signals."""

    @abstractmethod
    def rerank(
        self,
        results: List[SearchResult],
        parsed_query: ParsedQuery,
        top_k: int = 8,
    ) -> List[RerankedChunk]:
        ...


class IContextBuilder(ABC):
    """Merges re-ranked chunks into an optimised context window."""

    @abstractmethod
    def build_context(
        self,
        chunks: List[RerankedChunk],
        token_budget: int = 12_000,
    ) -> ContextWindow:
        ...


class IPromptBuilder(ABC):
    """Constructs the final LLM prompt from context + conversation history."""

    @abstractmethod
    def build_prompt(
        self,
        parsed_query: ParsedQuery,
        context: ContextWindow,
        history: Optional[ConversationHistory] = None,
    ) -> tuple[str, str]:
        """Returns (system_prompt, user_prompt)."""
        ...


class IResponseValidator(ABC):
    """Validates LLM output for hallucination and grounding."""

    @abstractmethod
    def validate(
        self,
        answer: str,
        chunks: List[RerankedChunk],
    ) -> ValidationResult:
        ...


class ICitationGenerator(ABC):
    """Generates structured citations from the answer + source chunks."""

    @abstractmethod
    def generate(
        self,
        answer: str,
        chunks: List[RerankedChunk],
    ) -> List[Citation]:
        ...
