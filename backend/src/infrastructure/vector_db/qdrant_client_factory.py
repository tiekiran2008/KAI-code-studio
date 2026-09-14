"""
qdrant_client_factory.py
========================
Module-level shared QdrantClient manager to prevent file lock collisions
when running Qdrant in embedded path mode (path=qdrant_db_local).
"""
from typing import Dict, Optional
from qdrant_client import QdrantClient
from src.core.config import settings

_SHARED_QDRANT_CLIENTS: Dict[str, QdrantClient] = {}


def get_shared_qdrant_client(url: str, api_key: Optional[str] = None) -> QdrantClient:
    """Returns a process-wide shared QdrantClient for the given URL/path and api_key."""
    effective_api_key = api_key if api_key is not None else (settings.QDRANT_API_KEY or None)
    cache_key = f"{url}::api_key={'set' if effective_api_key else 'none'}"

    if cache_key not in _SHARED_QDRANT_CLIENTS:
        if url.startswith("path="):
            client = QdrantClient(path=url.split("=", 1)[1])
        elif url == ":memory:":
            client = QdrantClient(location=":memory:")
        else:
            client = QdrantClient(url=url, api_key=effective_api_key)
        _SHARED_QDRANT_CLIENTS[cache_key] = client
    return _SHARED_QDRANT_CLIENTS[cache_key]
