"""
qdrant_client_factory.py
========================
Module-level shared QdrantClient manager to prevent file lock collisions
when running Qdrant in embedded path mode (path=qdrant_db_local).
"""
from typing import Dict
from qdrant_client import QdrantClient

_SHARED_QDRANT_CLIENTS: Dict[str, QdrantClient] = {}


def get_shared_qdrant_client(url: str) -> QdrantClient:
    """Returns a process-wide shared QdrantClient for the given URL/path."""
    if url not in _SHARED_QDRANT_CLIENTS:
        if url.startswith("path="):
            client = QdrantClient(path=url.split("=", 1)[1])
        elif url == ":memory:":
            client = QdrantClient(location=":memory:")
        else:
            client = QdrantClient(url=url)
        _SHARED_QDRANT_CLIENTS[url] = client
    return _SHARED_QDRANT_CLIENTS[url]
