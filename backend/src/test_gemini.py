import asyncio
import sys
import os

# Ensure the /app directory is in sys.path so 'src.*' imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import settings
from src.infrastructure.llm.llm_factory import create_llm_provider

async def test_gemini():
    print(f"Loaded Settings - LLM Provider: {settings.LLM_PROVIDER}")
    print(f"Loaded Settings - Gemini Model: {settings.GEMINI_MODEL}")
    
    try:
        provider = create_llm_provider()
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize LLM provider: {e}")
        sys.exit(1)
        
    print(f"Provider initialized successfully. Model: {provider.model_name}")
    
    try:
        print("\nSending request to Gemini: 'Reply with exactly: GEMINI_OK'")
        response = await provider.complete(prompt="Reply with exactly: GEMINI_OK")
        print("\n--- SUCCESS ---")
        print(f"Response: {response.content.strip()}")
        print(f"Token Usage: {response.total_tokens}")
    except Exception as e:
        error_msg = str(e)
        print("\n--- ERROR ---")
        if "401" in error_msg or "403" in error_msg or "unauthenticated" in error_msg.lower() or "forbidden" in error_msg.lower():
            print(f"Authentication Error (401/403): Please check if your GEMINI_API_KEY is valid.")
            print(f"Details: {error_msg}")
        elif any(s in error_msg for s in ["429", "RESOURCE_EXHAUSTED", "quota", "Quota", "rate limit"]):
            print(f"Quota/Rate Limit Error (429): You have exceeded your API limits.")
            print(f"Details: {error_msg}")
        else:
            print(f"Other API Error:")
            print(f"Details: {error_msg}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_gemini())
