"""
Memory Domain Entities
======================
Pure domain dataclasses representing the four memory types and shared
scoring metadata used by the Intelligent Memory & Context Management system.

Design Decisions
----------------
* **No framework deps** — stdlib only (dataclasses, enum, uuid, datetime).
  This keeps the domain layer dependency-free and maximally testable.
* **Four memory types** reflect cognitive science categories:
    - ShortTermMemory  → volatile session state (Redis-backed)
    - LongTermMemory   → durable user preferences (PostgreSQL-backed)
    - RepositoryMemory → per-repo knowledge cache (PostgreSQL + Qdrant)
    - EpisodicMemory   → historical agent sessions (PostgreSQL + Qdrant)
* **MemoryScore** is a value-object embedded in every memory record.
  It drives ranking, forgetting, consolidation, and expiry decisions.
* All IDs are UUIDs to enable cross-service portability.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class MemoryType(str, Enum):
    """Identifies which of the four memory stores a record belongs to."""
    SHORT_TERM  = "short_term"
    LONG_TERM   = "long_term"
    REPOSITORY  = "repository"
    EPISODIC    = "episodic"


class MemoryStatus(str, Enum):
    """Lifecycle state of a memory record."""
    ACTIVE   = "active"     # In regular use
    ARCHIVED = "archived"   # Low access, kept for historical queries
    EXPIRED  = "expired"    # TTL elapsed; scheduler can delete
    DELETED  = "deleted"    # GDPR-style soft-delete; PII purged


class EpisodeType(str, Enum):
    """Sub-category for EpisodicMemory entries."""
    DEBUGGING       = "debugging"
    CODE_REVIEW     = "code_review"
    EXPLANATION     = "explanation"
    DOCUMENTATION   = "documentation"
    TEST_GENERATION = "test_generation"
    CODE_ANALYSIS   = "code_analysis"
    SECURITY_REVIEW = "security_review"
    PERFORMANCE     = "performance"
    GENERAL         = "general"


class PreferredExplanationDepth(str, Enum):
    BRIEF      = "brief"
    STANDARD   = "standard"
    DETAILED   = "detailed"
    EXHAUSTIVE = "exhaustive"


# ---------------------------------------------------------------------------
# Memory Score — value object embedded in every memory record
# ---------------------------------------------------------------------------

@dataclass
class MemoryScore:
    """
    Scoring metadata used for ranking, forgetting, and consolidation.

    Fields
    ------
    importance      : 0.0–1.0. How significant this memory is to the user.
    confidence      : 0.0–1.0. How certain we are this memory is accurate.
    access_count    : Total times this memory was retrieved.
    last_accessed   : UTC timestamp of most-recent retrieval.
    decay_factor    : Multiplier applied during time-decay ranking (0.0–1.0).
    source          : Origin (e.g. "llm_inference", "user_explicit", "rag_pipeline").
    tags            : Free-form searchable labels.
    """
    importance:    float = 0.5
    confidence:    float = 0.8
    access_count:  int   = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    decay_factor:  float = 1.0
    source:        str   = "system"
    tags:          List[str] = field(default_factory=list)

    def effective_score(self) -> float:
        """
        Composite relevance score used for ranking and forgetting decisions.
        Formula: importance * confidence * decay_factor * log(1 + access_count)
        Clamped to [0.0, 1.0].
        """
        import math
        raw = (
            self.importance
            * self.confidence
            * self.decay_factor
            * math.log1p(self.access_count + 1)
        )
        return min(1.0, max(0.0, raw))


# ---------------------------------------------------------------------------
# Base memory entity — all four types extend this
# ---------------------------------------------------------------------------

@dataclass
class BaseMemory:
    """
    Shared fields across all memory types.

    Fields
    ------
    id            : UUID primary key.
    user_id       : Owner — used for user isolation and GDPR.
    repository_id : Optional repo scope — used for repository isolation.
    memory_type   : Discriminator for which store this lives in.
    content       : The raw memory text / JSON payload.
    summary       : Short one-line summary for fast display.
    version       : Monotonically increasing; incremented on every update.
    status        : Active / Archived / Expired / Deleted lifecycle state.
    score         : Embedded MemoryScore value object.
    created_at    : UTC creation timestamp.
    expires_at    : Optional TTL; None = no automatic expiry.
    metadata      : Arbitrary key/value bag for extensibility.
    """
    id:            str            = field(default_factory=lambda: str(uuid.uuid4()))
    user_id:       str            = ""
    repository_id: Optional[str]  = None
    memory_type:   MemoryType     = MemoryType.SHORT_TERM
    content:       str            = ""
    summary:       str            = ""
    version:       int            = 1
    status:        MemoryStatus   = MemoryStatus.ACTIVE
    score:         MemoryScore    = field(default_factory=MemoryScore)
    created_at:    datetime       = field(default_factory=datetime.utcnow)
    expires_at:    Optional[datetime] = None
    metadata:      Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """True if the TTL has elapsed."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def bump_access(self) -> None:
        """Increment access counter and refresh last_accessed timestamp."""
        self.score.access_count += 1
        self.score.last_accessed = datetime.utcnow()

    def increment_version(self) -> None:
        """Monotonically increment version on content changes."""
        self.version += 1


# ---------------------------------------------------------------------------
# 1. Short-Term Memory
# ---------------------------------------------------------------------------

@dataclass
class ShortTermMemory(BaseMemory):
    """
    Volatile session-scoped memory stored in Redis.

    Holds the active conversation, task context, execution plan snapshot,
    and recent retrieved document digests for the current session.

    Default TTL: 30 minutes (configurable via MEMORY_SHORT_TERM_TTL_SECONDS).
    """
    memory_type:          MemoryType     = MemoryType.SHORT_TERM
    session_id:           str            = ""
    conversation_turns:   List[Dict[str, Any]] = field(default_factory=list)
    active_plan:          Optional[Dict[str, Any]] = None
    current_task:         str            = ""
    recent_document_ids:  List[str]      = field(default_factory=list)


# ---------------------------------------------------------------------------
# 2. Long-Term Memory
# ---------------------------------------------------------------------------

@dataclass
class UserPreferences:
    """
    Structured personalization block embedded in LongTermMemory.
    The memory system learns these from interaction patterns.
    """
    preferred_languages:        List[str] = field(default_factory=list)
    preferred_frameworks:       List[str] = field(default_factory=list)
    preferred_testing_framework: str = ""
    preferred_response_format:  str = "markdown"
    explanation_depth:          PreferredExplanationDepth = PreferredExplanationDepth.STANDARD
    coding_conventions:         Dict[str, str] = field(default_factory=dict)
    frequently_accessed_repos:  List[str] = field(default_factory=list)
    frequently_asked_topics:    List[str] = field(default_factory=list)


@dataclass
class LongTermMemory(BaseMemory):
    """
    Durable user-level memory stored in PostgreSQL.

    Persists preferences, coding style, and distilled knowledge across
    sessions. Survives Redis TTL expiry.
    """
    memory_type:  MemoryType     = MemoryType.LONG_TERM
    preferences:  UserPreferences = field(default_factory=UserPreferences)
    fact:         str            = ""  # Distilled factual claim about the user
    topic:        str            = ""  # e.g. "language_preference", "framework_preference"


# ---------------------------------------------------------------------------
# 3. Repository Memory
# ---------------------------------------------------------------------------

@dataclass
class RepositoryMemory(BaseMemory):
    """
    Per-repository knowledge cache stored in PostgreSQL + Qdrant.

    Caches expensive analysis results (architecture summaries, module maps,
    dependency graphs) so they don't need to be re-derived on every query.
    """
    memory_type:          MemoryType     = MemoryType.REPOSITORY
    repo_summary:         str            = ""
    architecture_summary: str            = ""
    module_summaries:     Dict[str, str] = field(default_factory=dict)  # path -> summary
    dependency_summary:   str            = ""
    frequently_referenced_files: List[str] = field(default_factory=list)
    tech_stack:           List[str]      = field(default_factory=list)
    last_indexed_at:      Optional[datetime] = None


# ---------------------------------------------------------------------------
# 4. Episodic Memory
# ---------------------------------------------------------------------------

@dataclass
class EpisodicMemory(BaseMemory):
    """
    Historical session memories stored in PostgreSQL + Qdrant.

    Records the salient outputs of previous agent sessions so future
    sessions can reference prior reasoning, explanations, and decisions.
    """
    memory_type:       MemoryType   = MemoryType.EPISODIC
    episode_type:      EpisodeType  = EpisodeType.GENERAL
    session_id:        str          = ""
    query:             str          = ""
    agent_outputs:     Dict[str, Any] = field(default_factory=dict)
    final_answer:      str          = ""
    confidence_score:  float        = 0.0
    citations:         List[Dict[str, Any]] = field(default_factory=list)
    execution_trace:   List[Dict[str, Any]] = field(default_factory=list)
    lessons_learned:   str          = ""  # LLM-distilled insight from this session


# ---------------------------------------------------------------------------
# Memory Search Query — passed to every search operation
# ---------------------------------------------------------------------------

@dataclass
class MemorySearchQuery:
    """
    Encapsulates a semantic + filtered search request against the memory stores.
    """
    query_text:    str
    user_id:       str
    memory_types:  List[MemoryType]  = field(default_factory=lambda: list(MemoryType))
    repository_id: Optional[str]     = None
    session_id:    Optional[str]     = None
    tags:          List[str]         = field(default_factory=list)
    top_k:         int               = 5
    min_score:     float             = 0.0
    include_archived: bool           = False


# ---------------------------------------------------------------------------
# Memory Retrieval Result — returned by every search operation
# ---------------------------------------------------------------------------

@dataclass
class MemorySearchResult:
    """
    A ranked memory record returned by a search operation.
    """
    memory:       BaseMemory
    relevance_score: float = 0.0
    rank:         int      = 0


# ---------------------------------------------------------------------------
# Consolidation Report — output of background consolidation
# ---------------------------------------------------------------------------

@dataclass
class ConsolidationReport:
    """Summary produced by a single consolidation run."""
    run_id:           str = field(default_factory=lambda: str(uuid.uuid4()))
    memories_scanned: int = 0
    memories_merged:  int = 0
    memories_archived:int = 0
    memories_deleted: int = 0
    duration_ms:      float = 0.0
    errors:           List[str] = field(default_factory=list)
    ran_at:           datetime = field(default_factory=datetime.utcnow)
