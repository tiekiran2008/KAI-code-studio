"""
LLM Provider Interface
======================
Abstract interface for any LLM provider (Gemini, OpenAI, etc.).
The application layer depends only on this interface — never on SDK internals.
"""
from abc import ABC, abstractmethod
from src.domain.models.rag import LLMResponse


class ILLMProvider(ABC):
    """Contract that every LLM backend adapter must fulfil."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Send a prompt and return a structured LLMResponse."""
        ...

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """Estimate token count for a given text string."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable model identifier (e.g. 'gemini-1.5-pro')."""
        ...

    @property
    @abstractmethod
    def context_window_limit(self) -> int:
        """Maximum tokens this model can accept in a single request."""
        ...
