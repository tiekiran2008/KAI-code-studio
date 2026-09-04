"""
Memory Persistence Models (SQLAlchemy ORM)
==========================================
Defines the PostgreSQL table schemas for all four memory types.

Design Decisions
----------------
* **Unified `memories` table with a `memory_type` discriminator** keeps the
  schema simple and allows a single GIN index on `tags` to serve all types.
  Specialised columns (e.g. `session_id`, `episode_type`) are nullable and
  only populated for the relevant type.
* **JSONB columns** (`metadata_json`, `agent_outputs_json`, etc.) provide
  schema flexibility without ALTER TABLE for every new field.
* **`content_encrypted` flag** signals whether the `content` column holds a
  Fernet ciphertext; the repository layer checks this before exposing content.
* **Soft-delete via `status`** preserves audit trails while removing PII.
* **`version` column** supports optimistic concurrency control.
* **GIN index on `tags_json`** enables efficient tag-based searches without
  a full table scan.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import declarative_base

# Re-use the project's existing declarative Base so all tables register
# together and migrate together.
from src.infrastructure.persistence.base import Base


class DBMemory(Base):
    """
    Unified memory table.  Each row is one of the four memory types,
    distinguished by the `memory_type` column.
    """
    __tablename__ = "memories"

    # ------------------------------------------------------------------
    # Primary key & ownership
    # ------------------------------------------------------------------
    id            = Column(String(36), primary_key=True, comment="UUID v4")
    user_id       = Column(String(255), nullable=False, index=True, comment="Owner user ID")
    repository_id = Column(String(255), nullable=True, index=True, comment="Scoped repository ID")

    # ------------------------------------------------------------------
    # Discriminator & lifecycle
    # ------------------------------------------------------------------
    memory_type = Column(
        String(32), nullable=False, index=True,
        comment="short_term | long_term | repository | episodic",
    )
    status = Column(
        String(16), nullable=False, default="active", index=True,
        comment="active | archived | expired | deleted",
    )
    version = Column(Integer, nullable=False, default=1, comment="Optimistic concurrency version")

    # ------------------------------------------------------------------
    # Core content
    # ------------------------------------------------------------------
    content           = Column(Text, nullable=False, default="")
    content_encrypted = Column(Boolean, nullable=False, default=False,
                               comment="True when content holds Fernet ciphertext")
    summary           = Column(String(512), nullable=False, default="")

    # ------------------------------------------------------------------
    # Scoring / ranking fields (denormalised from MemoryScore value-object)
    # ------------------------------------------------------------------
    importance   = Column(Float, nullable=False, default=0.5)
    confidence   = Column(Float, nullable=False, default=0.8)
    access_count = Column(Integer, nullable=False, default=0)
    last_accessed = Column(DateTime, nullable=False, default=datetime.utcnow)
    decay_factor  = Column(Float, nullable=False, default=1.0)
    source        = Column(String(128), nullable=False, default="system")

    # Stored as a JSON array ["tag1", "tag2"] with a GIN index in Postgres
    tags_json = Column(JSON, nullable=False, default=list,
                       comment="Searchable string tags array")

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True,
                        comment="NULL means no TTL; scheduler checks this")

    # ------------------------------------------------------------------
    # Type-specific columns
    # ------------------------------------------------------------------

    # ShortTermMemory fields
    session_id         = Column(String(255), nullable=True, index=True)
    conversation_turns = Column(JSON, nullable=True, default=list)
    active_plan_json   = Column(JSON, nullable=True)
    current_task       = Column(String(512), nullable=True)

    # LongTermMemory fields
    preferences_json = Column(JSON, nullable=True,
                               comment="Serialised UserPreferences object")
    fact             = Column(Text, nullable=True)
    topic            = Column(String(128), nullable=True, index=True)

    # RepositoryMemory fields
    repo_summary          = Column(Text, nullable=True)
    architecture_summary  = Column(Text, nullable=True)
    module_summaries_json = Column(JSON, nullable=True)
    dependency_summary    = Column(Text, nullable=True)
    tech_stack_json       = Column(JSON, nullable=True)
    last_indexed_at       = Column(DateTime, nullable=True)
    frequently_ref_files  = Column(JSON, nullable=True)

    # EpisodicMemory fields
    episode_type      = Column(String(32), nullable=True, index=True)
    query             = Column(Text, nullable=True)
    agent_outputs_json = Column(JSON, nullable=True)
    final_answer      = Column(Text, nullable=True)
    confidence_score  = Column(Float, nullable=True)
    citations_json    = Column(JSON, nullable=True)
    execution_trace_json = Column(JSON, nullable=True)
    lessons_learned   = Column(Text, nullable=True)

    # Arbitrary extensibility bag
    metadata_json = Column(JSON, nullable=True, default=dict)

    # ------------------------------------------------------------------
    # Indexes (GIN on tags for array containment queries)
    # ------------------------------------------------------------------
    __table_args__ = (
        Index("ix_memories_user_type", "user_id", "memory_type"),
        Index("ix_memories_user_repo", "user_id", "repository_id"),
        Index("ix_memories_user_status", "user_id", "status"),
        Index("ix_memories_expires_at", "expires_at"),
    )
