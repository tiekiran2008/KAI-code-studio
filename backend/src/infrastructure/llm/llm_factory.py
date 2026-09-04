"""
LLM Factory
===========
Creates the appropriate ILLMProvider implementation based on application
settings. Raises a clear ConfigurationError if no API key is available.
"""
import logging

from src.domain.interfaces.llm import ILLMProvider
from src.core.config import settings

logger = logging.getLogger(__name__)


class LLMConfigurationError(Exception):
    """Raised when no usable LLM provider can be configured."""


def create_llm_provider() -> ILLMProvider:
    """
    Factory function — instantiates the LLM provider specified in settings.

    Priority:
    1. Uses `settings.LLM_PROVIDER` as the preferred provider.
    2. Falls back to the other provider if the preferred one has no API key.
    3. Raises LLMConfigurationError if no provider can be configured.
    """
    preferred = settings.LLM_PROVIDER.lower()

    def try_gemini() -> ILLMProvider:
        from src.infrastructure.llm.gemini_provider import GeminiProvider
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
        )

    def try_openai() -> ILLMProvider:
        from src.infrastructure.llm.openai_provider import OpenAIProvider
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
        )

    providers = {
        "gemini": (try_gemini, settings.GEMINI_API_KEY),
        "openai": (try_openai, settings.OPENAI_API_KEY),
    }

    # Try preferred provider first
    if preferred in providers:
        factory_fn, api_key = providers[preferred]
        if api_key:
            try:
                provider = factory_fn()
                logger.info("llm_provider_initialized", extra={"provider": preferred, "model": provider.model_name})
                return provider
            except Exception as exc:
                logger.warning(f"preferred_llm_provider_failed provider={preferred} error={str(exc)}")

    # Try fallback providers
    for name, (factory_fn, api_key) in providers.items():
        if name == preferred:
            continue
        if api_key:
            try:
                provider = factory_fn()
                logger.warning(
                    f"llm_provider_fallback preferred={preferred} actual={name} model={provider.model_name}"
                )
                return provider
            except Exception as exc:
                logger.warning(f"fallback_llm_provider_failed provider={name} error={str(exc)}")

    raise LLMConfigurationError(
        "No LLM provider could be configured. "
        "Set GEMINI_API_KEY or OPENAI_API_KEY in your environment or .env file."
    )
