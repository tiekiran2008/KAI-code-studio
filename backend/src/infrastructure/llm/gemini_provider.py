"""
Gemini LLM Provider
===================
Adapter implementing ILLMProvider over Google's GenAI SDK (google.genai).
Uses gemini-2.5-flash by default (configurable). Async calls are
dispatched via asyncio.to_thread since the SDK is synchronous.
Retries with exponential backoff are applied for transient errors.
"""
import asyncio
import logging
from typing import Optional

from google import genai
from google.genai import types
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.rag import LLMResponse

logger = logging.getLogger(__name__)

# Exceptions worth retrying (transient errors only).
# 429 ResourceExhausted = quota exceeded — do NOT retry, it won't help.
_QUOTA_EXCEEDED_STRINGS = (
    "429",
    "RESOURCE_EXHAUSTED",
    "quota",
    "Quota",
    "rate limit",
)


def _is_retryable(exc: Exception) -> bool:
    """Return True only for transient errors, not for quota/billing failures."""
    msg = str(exc)
    return not any(s in msg for s in _QUOTA_EXCEEDED_STRINGS)


_RETRYABLE = (Exception,)  # Narrowed at runtime via _is_retryable predicate


class GeminiProvider(ILLMProvider):
    """Google Gemini adapter using the google-genai SDK."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiProvider")
        self._client = genai.Client(api_key=api_key)
        self._model_name = model

    # ------------------------------------------------------------------
    # ILLMProvider implementation
    # ------------------------------------------------------------------

    async def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Send a completion request to Gemini and return structured response."""
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = await asyncio.to_thread(self._sync_complete, full_prompt, max_tokens, temperature)
        return response

    async def count_tokens(self, text: str) -> int:
        """Estimate token count using the Gemini token counting API."""
        try:
            result = await asyncio.to_thread(
                self._client.models.count_tokens,
                model=self._model_name,
                contents=text,
            )
            return result.total_tokens
        except Exception as exc:
            logger.warning("gemini_token_count_failed: %s — falling back to char estimate", exc)
            return len(text) // 4  # ~4 chars per token fallback

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def context_window_limit(self) -> int:
        # gemini-2.5-flash supports up to 1M+ tokens; we cap at 128k for safety
        return 128_000

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    def _sync_complete(self, prompt: str, max_tokens: int, temperature: float) -> LLMResponse:
        """Synchronous Gemini API call — wrapped in to_thread by the caller."""
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
        )

        # Extract token usage if available (depends on model/region)
        prompt_tokens = 0
        completion_tokens = 0
        try:
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
        except Exception:
            pass  # Usage metadata not always available

        return LLMResponse(
            content=response.text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            model_name=self._model_name,
            finish_reason="stop",
            raw_response=response,
        )
