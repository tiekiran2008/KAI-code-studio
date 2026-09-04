"""
OpenAI LLM Provider
===================
Adapter implementing ILLMProvider over the OpenAI async client.
Token counting uses tiktoken for accurate billing estimation.
Retries are handled by tenacity with exponential backoff.
"""
import logging
from typing import Optional

import tiktoken
from openai import AsyncOpenAI, RateLimitError, APIConnectionError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.rag import LLMResponse

logger = logging.getLogger(__name__)

_RETRYABLE = (RateLimitError, APIConnectionError, APITimeoutError)


class OpenAIProvider(ILLMProvider):
    """OpenAI adapter using the official async client."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIProvider")
        self._client = AsyncOpenAI(api_key=api_key)
        self._model_name = model

        # Load tokenizer (falls back gracefully on unknown models)
        try:
            self._tokenizer = tiktoken.encoding_for_model(model)
        except KeyError:
            self._tokenizer = tiktoken.get_encoding("cl100k_base")

    # ------------------------------------------------------------------
    # ILLMProvider implementation
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(_RETRYABLE),
        reraise=True,
    )
    async def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Send a chat completion request to OpenAI."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._model_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            content=choice.message.content or "",
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            model_name=self._model_name,
            finish_reason=choice.finish_reason or "stop",
            raw_response=response,
        )

    async def count_tokens(self, text: str) -> int:
        """Accurate token count using tiktoken (no API call required)."""
        return len(self._tokenizer.encode(text))

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def context_window_limit(self) -> int:
        # gpt-4o supports 128k tokens
        return 128_000
