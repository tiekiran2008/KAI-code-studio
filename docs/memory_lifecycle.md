# Memory Lifecycle & Consolidation

This document describes how memory records transition through states over time, preventing context bloat and ensuring relevance.

## Memory Status States

A memory record (`BaseMemory.status`) can be in one of three states:

1. **ACTIVE**: The memory is valid, searchable, and actively considered during context enrichment.
2. **ARCHIVED**: The memory is retained in PostgreSQL for historical auditing or background learning but is removed from the Qdrant vector index. It will not appear in standard semantic searches.
3. **DELETED**: A tombstone state indicating the memory has been GDPR soft-deleted. Its content is scrubbed, and the vector is removed.

## Scoring and Decay

Every memory has a `MemoryScore` object tracking its utility:
- **Importance (0.0 to 1.0):** Assigned at creation (e.g., higher for explicit user preferences, lower for general episodic traces).
- **Confidence (0.0 to 1.0):** The agent's confidence in the memory's factual accuracy.
- **Access Count:** Incremented every time the memory is returned in a search and hydrated into context.
- **Last Accessed:** Timestamp of the last hit.
- **Decay Factor:** A multiplier (default 1.0) used to artificially suppress older, less relevant memories during consolidation.

## Background Consolidation

The `MemoryManager.consolidate()` method runs periodically (e.g., via a Celery beat task or an API trigger) to perform background hygiene.

### Phase 1: Expiration
- Queries PostgreSQL for memories where `expires_at < NOW()`.
- **Action:** Soft-deletes the records (removes from Qdrant, scrubs content, sets status to `DELETED`).
- *Note:* Short-Term memories use Redis TTL natively, so this phase primarily targets Long-Term memories with finite retention policies.

### Phase 2: Archiving
- Queries PostgreSQL for active memories that have not been accessed in `MEMORY_CONSOLIDATION_INACTIVE_DAYS` (default 90 days).
- **Action:** Reduces the `decay_factor` by 20% and sets the status to `ARCHIVED`. The vector is deleted from Qdrant to save indexing space.

### Phase 3: Merging (Future Roadmap)
- Identifies semantically identical or highly overlapping memories (using a combination of Qdrant batch search and LLM summarization).
- **Action:** Consolidates multiple records into a single, higher-importance memory, deleting the old granular records.

## Updates and Versioning

When a memory is updated (e.g., a user's coding preference changes):
1. The `MemoryManager` retrieves the existing entity.
2. Changes are merged, and `increment_version()` is called.
3. The `PostgresMemoryRepository` executes an `UPDATE` with a `WHERE version = old_version` clause.
4. If 0 rows are updated, an optimistic concurrency exception is raised.
5. If the `content` or `summary` changed, the manager recalculates the embedding and upserts Qdrant.
