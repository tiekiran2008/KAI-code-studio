# Intelligent Memory Architecture

This document details the architecture of the Phase 7 Intelligent Memory subsystem for the AI Software Engineering Agent.

## Overview

The memory subsystem provides the agent with short-term context tracking, long-term preference learning, episodic reasoning recall, and repository-wide architectural understanding. It implements a **fan-out search architecture** that separates fast semantic vector retrieval from structured relational data storage, enforcing strict user isolation and GDPR compliance.

## Storage Triad

The subsystem relies on three specialized storage technologies:

1. **Redis (Short-Term Session Cache)**
   - **Purpose:** Volatile memory for active agent sessions.
   - **Data:** `ShortTermMemory` (current task, active plan, conversation history).
   - **Characteristics:** Fast key-value access, automatic TTL expiration (default 30 mins). Namespaced by `user_id` and `session_id`.

2. **Qdrant (Vector Store)**
   - **Purpose:** Semantic similarity search.
   - **Data:** 384-dimensional embeddings of memory contents (via `all-MiniLM-L6-v2`) and a small metadata payload for filtering.
   - **Characteristics:** Single collection (`memories`) with filtering on a `memory_type` field. Enforces user isolation via a mandatory `must` filter on `user_id` during search.

3. **PostgreSQL (Relational Store)**
   - **Purpose:** Source of truth, structured queries, and GDPR lifecycle management.
   - **Data:** Serialized domain entities (`BaseMemory` subclasses) stored in a unified `DBMemory` table using SQLAlchemy.
   - **Characteristics:** Uses `JSONB` for flexible schema evolution per memory type, optimistic concurrency control via a `version` column, and optional Fernet-based field-level encryption for sensitive data at rest.

## Core Components

### 1. Domain Layer (`src/domain/memory/entities.py`)
- Defines standard pure-Python models for `ShortTermMemory`, `LongTermMemory`, `EpisodicMemory`, and `RepositoryMemory`.
- Encapsulates ranking logic within `MemoryScore` (importance, confidence, access count, decay factor).

### 2. Infrastructure Ports (`src/domain/memory/ports.py`)
- Defines interfaces (`IMemoryRepository`, `IMemoryVectorStore`, `ISessionCache`, `IMemoryManager`) ensuring the application layer is decoupled from concrete database drivers.

### 3. Memory Manager (`src/infrastructure/memory/memory_manager.py`)
- The central orchestrator. 
- Implements **fan-out search**: queries Qdrant for semantic similarity, retrieves matching IDs, hydrates full entities from PostgreSQL, and ranks them using a composite score (similarity + importance + recency).
- Handles context deduplication via token-overlap checks to prevent redundant context injection.

### 4. Memory Service (`src/application/services/memory_service.py`)
- Application façade injected into Use Cases.
- Provides high-level methods like `enrich_agent_context()`, `save_episode()`, and `update_user_preferences()`.

## Data Flow (Pre-Execution Context Enrichment)

1. Agent execution begins via `ExecuteAgentWorkflowUseCase`.
2. Uses `MemoryService` to initialize short-term session memory.
3. Calls `MemoryService.enrich_agent_context(query)`.
4. `MemoryManager` embeds the query and searches Qdrant (filtered by `user_id`).
5. Hydrates hits from PostgreSQL and applies composite ranking.
6. Filters out memories that semantically overlap with existing RAG context.
7. Prepends the resulting structured text to the LangGraph agent state.

## Security and Compliance

- **User Isolation:** All repository and vector operations strictly require `user_id`. It is impossible to fetch a memory without the owner's ID.
- **GDPR Soft-Delete:** `forget_memory(hard=False)` sets status to `DELETED`, scrubs the text content, and removes the vector from Qdrant, retaining the ID tombstone.
- **GDPR Hard-Delete:** `forget_user()` executes `DELETE` statements on Postgres and Qdrant, completely erasing all trace of the user's data (Article 17 Right to Erasure).
- **Encryption at Rest:** Opt-in field-level encryption via `FernetMemoryEncryptor` secures the `content` and `summary` columns in PostgreSQL.
