"""
Memory Domain Ports (Abstract Interfaces)
==========================================
Defines every abstract interface that the memory subsystem exposes and
depends on. Application and infrastructure layers depend only on these
abstractions — never on concrete implementations.

Design Principles
-----------------
* **Dependency Inversion** (SOLID-D) — high-level modules depend on these
  abstractions, not on SQLAlchemy / Redis / Qdrant directly.
* **Interface Segregation** (SOLID-I) — separate, small interfaces for each
  storage concern (structured DB, vector store, session cache, encryption).
* **Open/Closed** (SOLID-O) — adding a new storage backend requires only a
  new implementation class, not changes to callers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.domain.memory.entities import (
    BaseMemory,
    ConsolidationReport,
    EpisodicMemory,
    LongTermMemory,
    MemorySearchQuery,
    MemorySearchResult,
    MemoryType,
    RepositoryMemory,
    ShortTermMemory,
)


# ---------------------------------------------------------------------------
# IMemoryRepository — structured (PostgreSQL) persistence
# ---------------------------------------------------------------------------

class IMemoryRepository(ABC):
    """
    CRUD interface for durable, structured memory storage.
    The default implementation targets PostgreSQL via SQLAlchemy.
    Swap for any other RDBMS or document store without touching callers.
    """

    @abstractmethod
    async def save(self, memory: BaseMemory) -> BaseMemory:
        """Persist a new memory record. Returns the saved entity with DB-assigned fields."""
        ...

    @abstractmethod
    async def update(self, memory: BaseMemory) -> BaseMemory:
        """
        Update an existing memory record.
        Must increment version and update updated_at automatically.
        """
        ...

    @abstractmethod
    async def get_by_id(self, memory_id: str, user_id: str) -> Optional[BaseMemory]:
        """
        Fetch a single memory by its UUID.
        user_id enforces ownership isolation — must raise PermissionError
        if the record belongs to a different user.
        """
        ...

    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        repository_id: Optional[str] = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BaseMemory]:
        """Paginated list of memories belonging to user_id."""
        ...

    @abstractmethod
    async def search_by_tags(
        self,
        user_id: str,
        tags: List[str],
        memory_type: Optional[MemoryType] = None,
        limit: int = 20,
    ) -> List[BaseMemory]:
        """Exact-match tag filter backed by a GIN index."""
        ...

    @abstractmethod
    async def soft_delete(self, memory_id: str, user_id: str) -> None:
        """
        GDPR-compliant soft delete: set status=DELETED and scrub PII from
        the content field. Physical row is retained for audit purposes.
        """
        ...

    @abstractmethod
    async def hard_delete(self, memory_id: str, user_id: str) -> None:
        """Physical deletion of the row. Use only for GDPR erasure."""
        ...

    @abstractmethod
    async def hard_delete_all_for_user(self, user_id: str) -> int:
        """GDPR right-to-erasure: delete every record belonging to user_id. Returns count."""
        ...

    @abstractmethod
    async def get_expired(self, limit: int = 100) -> List[BaseMemory]:
        """Return records whose expires_at < utcnow for the consolidation scheduler."""
        ...

    @abstractmethod
    async def get_inactive(
        self,
        days_inactive: int = 90,
        limit: int = 200,
    ) -> List[BaseMemory]:
        """Return records not accessed for N days — candidates for archiving."""
        ...

    @abstractmethod
    async def update_score(self, memory_id: str, score_delta: Dict[str, Any]) -> None:
        """Partial update of scoring fields (access_count, last_accessed, decay_factor)."""
        ...


# ---------------------------------------------------------------------------
# IMemoryVectorStore — semantic (Qdrant) retrieval
# ---------------------------------------------------------------------------

class IMemoryVectorStore(ABC):
    """
    Interface for semantic similarity search over memory embeddings.
    Default implementation uses Qdrant; swap for Pinecone, Weaviate, etc.
    """

    @abstractmethod
    async def upsert(
        self,
        memory_id: str,
        user_id: str,
        memory_type: MemoryType,
        embedding: List[float],
        payload: Dict[str, Any],
    ) -> None:
        """
        Insert or update a vector point.
        payload stores enough metadata to reconstruct a search result
        without a round-trip to PostgreSQL.
        """
        ...

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        user_id: str,
        memory_types: Optional[List[MemoryType]] = None,
        repository_id: Optional[str] = None,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Semantic nearest-neighbour search filtered by user_id.
        Returns a list of payloads with an injected 'score' key.
        """
        ...

    @abstractmethod
    async def delete(self, memory_id: str, user_id: str) -> None:
        """Remove a single vector point — called on soft/hard delete."""
        ...

    @abstractmethod
    async def delete_all_for_user(self, user_id: str) -> None:
        """GDPR erasure: remove all vector points for user_id."""
        ...

    @abstractmethod
    async def collection_info(self) -> Dict[str, Any]:
        """Return collection stats (point count, vector config) for health checks."""
        ...


# ---------------------------------------------------------------------------
# ISessionCache — volatile (Redis) short-term session storage
# ---------------------------------------------------------------------------

class ISessionCache(ABC):
    """
    Interface for fast, volatile session memory.
    Default implementation uses Redis. Swap for Memcached or in-process
    dict for tests.
    """

    @abstractmethod
    async def set(
        self,
        session_id: str,
        user_id: str,
        memory: ShortTermMemory,
        ttl_seconds: int = 1800,
    ) -> None:
        """Serialise and store the ShortTermMemory for this session."""
        ...

    @abstractmethod
    async def get(
        self,
        session_id: str,
        user_id: str,
    ) -> Optional[ShortTermMemory]:
        """Deserialise and return ShortTermMemory, or None if expired/absent."""
        ...

    @abstractmethod
    async def delete(self, session_id: str, user_id: str) -> None:
        """Remove session memory (logout / explicit clear)."""
        ...

    @abstractmethod
    async def extend_ttl(self, session_id: str, user_id: str, ttl_seconds: int) -> None:
        """Reset the expiry on an active session (keep-alive)."""
        ...

    @abstractmethod
    async def exists(self, session_id: str, user_id: str) -> bool:
        """Check whether a session key is present (without deserialising)."""
        ...


# ---------------------------------------------------------------------------
# IMemoryEncryptor — field-level encryption for sensitive content
# ---------------------------------------------------------------------------

class IMemoryEncryptor(ABC):
    """
    Interface for encrypting/decrypting the `content` field of memories
    that carry PII or sensitive code snippets.
    Default implementation uses Fernet (AES-128-CBC + HMAC).
    """

    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """Return a base64-encoded ciphertext string."""
        ...

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        """Return the original plaintext, raising ValueError on tamper."""
        ...


# ---------------------------------------------------------------------------
# IMemoryManager — high-level orchestrator (primary entrypoint for callers)
# ---------------------------------------------------------------------------

class IMemoryManager(ABC):
    """
    Top-level interface that all callers (use-cases, agents, API layer) depend on.
    Orchestrates the three storage backends and implements cross-cutting concerns:
    ranking, deduplication, consolidation, and GDPR operations.
    """

    # ---- Create / Update ----

    @abstractmethod
    async def create_short_term(
        self,
        user_id: str,
        session_id: str,
        memory: ShortTermMemory,
    ) -> ShortTermMemory:
        """Persist a new short-term session memory to Redis."""
        ...

    @abstractmethod
    async def create_long_term(
        self,
        user_id: str,
        memory: LongTermMemory,
    ) -> LongTermMemory:
        """Persist a new long-term user preference/fact to PostgreSQL + Qdrant."""
        ...

    @abstractmethod
    async def create_repository_memory(
        self,
        user_id: str,
        memory: RepositoryMemory,
    ) -> RepositoryMemory:
        """Persist a new repository knowledge record to PostgreSQL + Qdrant."""
        ...

    @abstractmethod
    async def create_episodic(
        self,
        user_id: str,
        memory: EpisodicMemory,
    ) -> EpisodicMemory:
        """Persist a new episodic session record to PostgreSQL + Qdrant."""
        ...

    @abstractmethod
    async def update_memory(
        self,
        memory_id: str,
        user_id: str,
        updates: Dict[str, Any],
    ) -> BaseMemory:
        """
        Partial update of a memory record.
        Enforces ownership, increments version, handles conflict resolution.
        """
        ...

    # ---- Search / Retrieval ----

    @abstractmethod
    async def search(self, query: MemorySearchQuery) -> List[MemorySearchResult]:
        """
        Multi-store semantic search.
        Embeds query_text, queries Qdrant, hydrates from PostgreSQL,
        and returns ranked, deduplicated results.
        """
        ...

    @abstractmethod
    async def get_session_memory(
        self,
        session_id: str,
        user_id: str,
    ) -> Optional[ShortTermMemory]:
        """Retrieve active session memory from Redis."""
        ...

    @abstractmethod
    async def enrich_context(
        self,
        query_text: str,
        user_id: str,
        session_id: Optional[str],
        repository_id: Optional[str],
        existing_rag_context: str,
        token_budget: int = 2000,
    ) -> str:
        """
        Pre-execution context enrichment hook.
        Searches all memory stores, ranks results, deduplicates against
        existing_rag_context, and returns a memory-augmented context string
        within the token_budget.
        """
        ...

    # ---- Lifecycle ----

    @abstractmethod
    async def forget(self, memory_id: str, user_id: str, hard: bool = False) -> None:
        """
        Forget a single memory.
        Soft delete by default (GDPR-compliant PII scrubbing).
        hard=True physically removes the row and Qdrant vector.
        """
        ...

    @abstractmethod
    async def forget_user(self, user_id: str) -> int:
        """GDPR right-to-erasure: remove ALL memories for a user. Returns count deleted."""
        ...

    @abstractmethod
    async def consolidate(self) -> ConsolidationReport:
        """
        Background consolidation pass.
        Merges similar memories, archives inactive ones, deletes expired ones.
        Should be called by a scheduler, not on the hot request path.
        """
        ...

    # ---- Read ----

    @abstractmethod
    async def get_by_id(self, memory_id: str, user_id: str) -> Optional[BaseMemory]:
        """Fetch a memory by ID with ownership check."""
        ...

    @abstractmethod
    async def list_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        repository_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BaseMemory]:
        """Paginated list of memories for a user."""
        ...
