import asyncio
import os
import sys
import logging
from src.core.config import settings
from src.infrastructure.llm.llm_factory import create_llm_provider
from src.domain.interfaces.llm import ILLMProvider

# Configure logging to see detailed output
logging.basicConfig(level=logging.INFO)

async def test_connectivity():
    print(f"LLM_PROVIDER: {settings.LLM_PROVIDER}")
    print(f"GEMINI_API_KEY is configured: {bool(settings.GEMINI_API_KEY)}")
    print(f"GEMINI_MODEL: {settings.GEMINI_MODEL}")
    
    if not settings.GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY is not set.")
        sys.exit(1)

    try:
        provider: ILLMProvider = create_llm_provider()
        print(f"Provider created: {type(provider).__name__}")
        print(f"Model used: {provider.model_name}")
        
        print("Testing basic completion...")
        response = await provider.complete(prompt="Say 'Hello, World!'")
        
        print("\nSUCCESS: Gemini connectivity works!")
        print(f"Response: {response.content}")
        print(f"Tokens: {response.total_tokens}")
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: Failed to connect to Gemini API: {type(e).__name__}: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_connectivity())
