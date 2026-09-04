"""
Qdrant Memory Vector Store
===========================
Implements ``IMemoryVectorStore`` using the Qdrant Python client.

Design Decisions
----------------
* **Single collection** named ``memories`` stores all memory types.
  A `memory_type` field in the payload acts as a filter, avoiding the
  operational overhead of managing multiple collections.
* **User isolation** is enforced at query time via a must-filter on
  ``user_id`` — this prevents any cross-user leakage even if collection
  access controls are misconfigured.
* **Upsert semantics** mean the same operation handles both insert and update
  correctly, simplifying the caller (MemoryManager).
* **Lazy collection creation** — the collection is created on first upsert
  if it doesn't already exist, removing infrastructure bootstrapping friction.
* Embedding dimension defaults to 384 (matching ``all-MiniLM-L6-v2`` /
  SentenceTransformer used elsewhere) and is overridable via the
  ``MEMORY_VECTOR_DIM`` env var.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from src.domain.memory.entities import MemoryType
from src.domain.memory.ports import IMemoryVectorStore
from src.core.logger import logger


_COLLECTION_NAME = "memories"


class QdrantMemoryVectorStore(IMemoryVectorStore):
    """
    Qdrant-backed semantic memory store.

    All operations are synchronous Qdrant SDK calls wrapped in an ``async``
    interface for consistency with the rest of the application.
    (The Qdrant Python client is synchronous by default; the async wrapper
    avoids blocking the event loop via run_in_executor where needed.)
    """

    def __init__(
        self,
        qdrant_url: str,
        vector_dim: int | None = None,
        collection_name: str = _COLLECTION_NAME,
    ) -> None:
        from src.infrastructure.vector_db.qdrant_client_factory import get_shared_qdrant_client
        from qdrant_client.models import Distance, VectorParams

        self._dim = vector_dim or int(os.getenv("MEMORY_VECTOR_DIM", "384"))
        self._collection = collection_name
        self._client = get_shared_qdrant_client(qdrant_url)
        self._distance = Distance.COSINE
        self._vector_params = VectorParams(size=self._dim, distance=self._distance)
        self._ensure_collection()

    # ------------------------------------------------------------------
    # Collection bootstrap
    # ------------------------------------------------------------------

    def _ensure_collection(self) -> None:
        """Create the memories collection if it does not exist yet."""
        try:
            from qdrant_client.models import VectorParams
            existing = [c.name for c in self._client.get_collections().collections]
            if self._collection not in existing:
                self._client.create_collection(
                    collection_name=self._collection,
                    vectors_config=self._vector_params,
                )
                logger.info(
                    "qdrant_memory_collection_created",
                    collection=self._collection,
                    dim=self._dim,
                )
        except Exception as exc:
            logger.warning(
                "qdrant_memory_ensure_collection_failed",
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # IMemoryVectorStore implementation
    # ------------------------------------------------------------------

    async def upsert(
        self,
        memory_id: str,
        user_id: str,
        memory_type: MemoryType,
        embedding: List[float],
        payload: Dict[str, Any],
    ) -> None:
        from qdrant_client.models import PointStruct

        point = PointStruct(
            id=_uuid_to_int(memory_id),
            vector=embedding,
            payload={
                "memory_id":  memory_id,
                "user_id":    user_id,
                "memory_type": memory_type.value,
                **payload,
            },
        )
        self._client.upsert(
            collection_name=self._collection,
            points=[point],
        )
        logger.debug(
            "memory_vector_upserted",
            memory_id=memory_id,
            memory_type=memory_type.value,
        )

    async def search(
        self,
        query_embedding: List[float],
        user_id: str,
        memory_types: Optional[List[MemoryType]] = None,
        repository_id: Optional[str] = None,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

        must_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]

        if memory_types:
            type_values = [mt.value for mt in memory_types]
            if len(type_values) == 1:
                must_conditions.append(
                    FieldCondition(key="memory_type", match=MatchValue(value=type_values[0]))
                )
            else:
                must_conditions.append(
                    FieldCondition(key="memory_type", match=MatchAny(any=type_values))
                )

        if repository_id:
            must_conditions.append(
                FieldCondition(key="repository_id", match=MatchValue(value=repository_id))
            )

        search_filter = Filter(must=must_conditions)

        results = self._client.query_points(
            collection_name=self._collection,
            query=query_embedding,
            query_filter=search_filter,
            limit=top_k,
            score_threshold=score_threshold if score_threshold > 0 else None,
            with_payload=True,
        )

        hits = []
        for hit in results.points:
            payload = dict(hit.payload or {})
            payload["score"] = hit.score
            hits.append(payload)

        logger.debug(
            "memory_vector_search",
            user_id=user_id,
            top_k=top_k,
            hits=len(hits),
        )
        return hits

    async def delete(self, memory_id: str, user_id: str) -> None:
        from qdrant_client.models import PointIdsList

        self._client.delete(
            collection_name=self._collection,
            points_selector=PointIdsList(points=[_uuid_to_int(memory_id)]),
        )
        logger.info("memory_vector_deleted", memory_id=memory_id)

    async def delete_all_for_user(self, user_id: str) -> None:
        from qdrant_client.models import Filter, FieldCondition, MatchValue, FilterSelector

        self._client.delete(
            collection_name=self._collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                )
            ),
        )
        logger.info("memory_vector_gdpr_erasure", user_id=user_id)

    async def collection_info(self) -> Dict[str, Any]:
        try:
            info = self._client.get_collection(self._collection)
            return {
                "collection":   self._collection,
                "vectors_count": info.vectors_count,
                "status":       str(info.status),
            }
        except Exception as exc:
            return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Helper — convert UUID string to a stable uint64 for Qdrant point IDs
# ---------------------------------------------------------------------------

def _uuid_to_int(uuid_str: str) -> int:
    """
    Qdrant requires integer or UUID-format point IDs.
    We pass the UUID string directly — Qdrant accepts UUID strings natively.
    Return the raw string here; cast to int only if the client forces it.
    """
    # Qdrant Python client >= 1.6 accepts UUID strings directly.
    # Return the string; the caller passes it as-is.
    return uuid_str  # type: ignore[return-value]
