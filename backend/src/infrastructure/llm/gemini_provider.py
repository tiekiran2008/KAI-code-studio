"""
Gemini LLM Provider
===================
Adapter implementing ILLMProvider over Google's GenAI SDK (google.genai).
Uses gemini-3.6-flash by default (configurable via GEMINI_MODEL). Async calls are
dispatched via asyncio.to_thread since the SDK is synchronous.
Retries with Retry-After backoff are applied for rate limits (429) and transient errors.
"""
import asyncio
import logging
import re
import time
from typing import Optional

from google import genai
from google.genai import types

from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.rag import LLMResponse

logger = logging.getLogger(__name__)

# Mapping of deprecated or unsupported model identifiers to the current supported model
_DEPRECATED_MODELS = {
    "gemini-2.5-flash": "gemini-3.6-flash",
    "gemini-2.5-pro": "gemini-3.6-flash",
    "gemini-1.5-flash": "gemini-3.6-flash",
    "gemini-1.5-pro": "gemini-3.6-flash",
    "gemini-3.1-pro": "gemini-3.6-flash",
}


def _extract_retry_delay(exc: Exception, default_delay: float = 2.0) -> float:
    """Extract retryDelay from Google RPC error details or error message safely."""
    msg = str(exc)
    # 1. Search for 'retry in Xs' or 'retryDelay': 'Xs' pattern in exception message
    m = re.search(r"retry(?:\s+in|\s*Delay[\'\"]?\s*:\s*[\'\"]?)\s*(\d+(?:\.\d+)?)s?", msg, re.IGNORECASE)
    if m:
        try:
            val = float(m.group(1))
            if 0 < val <= 90:
                return val
        except (ValueError, TypeError):
            pass

    # 2. Check structured exception attributes/details if present
    if hasattr(exc, "details"):
        try:
            details = getattr(exc, "details", [])
            if isinstance(details, list):
                for d in details:
                    if isinstance(d, dict) and "retryDelay" in d:
                        raw = str(d["retryDelay"]).rstrip("s")
                        val = float(raw)
                        if 0 < val <= 90:
                            return val
        except Exception:
            pass

    return default_delay


class GeminiProvider(ILLMProvider):
    """Google Gemini adapter using the google-genai SDK."""

    def __init__(self, api_key: str, model: str = "gemini-3.6-flash") -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiProvider")
        self._api_key = api_key
        self._client = genai.Client(api_key=api_key)
        # Normalize deprecated model names
        effective_model = _DEPRECATED_MODELS.get(model, model)
        if not effective_model or effective_model.startswith("gemini-2.5") or effective_model.startswith("gemini-1.5"):
            effective_model = "gemini-3.6-flash"
        self._model_name = effective_model

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
            logger.info("gemini_count_tokens_start effective_model=%s", self._model_name)
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
        # gemini-3.6-flash supports large context windows; capped at 128k for safety
        return 128_000

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sync_complete(self, prompt: str, max_tokens: int, temperature: float) -> LLMResponse:
        """Synchronous Gemini API call with safe Retry-After backoff for 429 rate limits."""
        max_attempts = 2

        for attempt in range(1, max_attempts + 1):
            logger.info("effective_model=%s", self._model_name)
            logger.info(
                "gemini_api_call_start effective_model=%s attempt=%d max_attempts=%d",
                self._model_name,
                attempt,
                max_attempts,
            )
            try:
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    ),
                )

                prompt_tokens = 0
                completion_tokens = 0
                try:
                    if hasattr(response, "usage_metadata") and response.usage_metadata:
                        prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                        completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
                except Exception:
                    pass

                return LLMResponse(
                    content=response.text or "",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    model_name=self._model_name,
                    finish_reason="stop",
                    raw_response=response,
                )

            except Exception as exc:
                msg = str(exc)
                # Remove any occurrence of API key in error messages
                if self._api_key and self._api_key in msg:
                    msg = msg.replace(self._api_key, "[REDACTED_API_KEY]")

                # 1. Fatal: 404 / model not found — do NOT retry
                if any(s in msg for s in ("404", "NOT_FOUND", "no longer available", "is not found", "not supported")):
                    logger.error("gemini_model_unavailable: %s", msg)
                    raise ValueError("Configured AI model is unavailable. Check GEMINI_MODEL in backend config.") from None

                # 2. Rate limit: 429 / RESOURCE_EXHAUSTED — backoff using Retry-After
                if any(s in msg for s in ("429", "RESOURCE_EXHAUSTED", "quota", "Quota", "rate limit")):
                    delay = _extract_retry_delay(exc, default_delay=min(3.0 * attempt, 30.0))
                    logger.warning(
                        "gemini_rate_limit_encountered attempt=%d max_attempts=%d retry_after_s=%.2f model=%s",
                        attempt,
                        max_attempts,
                        delay,
                        self._model_name,
                    )
                    if attempt < max_attempts:
                        # Cap wait at 15s — if quota is exhausted (Retry-After ~57s)
                        # waiting the full amount rarely helps and causes client timeouts.
                        sleep_s = min(delay + 1.0, 15.0)
                        logger.warning("gemini_rate_limit_retry_sleep sleep_s=%.1f (capped)", sleep_s)
                        time.sleep(sleep_s)
                        continue
                    else:
                        logger.error("gemini_rate_limit_exhausted_after_retries attempts=%d", max_attempts)
                        raise ValueError("Gemini API rate limit / quota exceeded. Please wait a moment and retry.") from None

                # 3. Fatal: Authentication / Invalid argument — do NOT retry
                if any(s in msg for s in ("API_KEY_INVALID", "INVALID_ARGUMENT", "400", "403", "PERMISSION_DENIED")):
                    logger.error("gemini_client_error: %s", msg)
                    raise ValueError(f"Gemini client error: {msg}") from None

                # 4. Transient network error — retry with linear backoff
                if attempt < max_attempts:
                    sleep_s = 2.0 * attempt
                    logger.warning("gemini_transient_error_retry attempt=%d sleep_s=%.1f", attempt, sleep_s)
                    time.sleep(sleep_s)
                    continue
                else:
                    logger.error("gemini_generate_failed: %s", msg)
                    raise ValueError(f"Gemini generation error: {msg}") from None

        raise ValueError("Gemini generation failed after retries")

