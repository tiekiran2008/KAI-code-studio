# Memory Sequence Diagrams

This document illustrates the interaction between the multi-agent workflow and the memory subsystem during a typical execution cycle.

## Pre-Execution: Context Enrichment

Before the LangGraph workflow begins, the `ExecuteAgentWorkflowUseCase` enriches the initial state with semantic memory.

```mermaid
sequenceDiagram
    participant UseCase as ExecuteAgentWorkflowUseCase
    participant MemSvc as MemoryService
    participant MemMgr as MemoryManager
    participant Cache as RedisSessionCache
    participant VStore as QdrantVectorStore
    participant DB as PostgresRepository

    UseCase->>MemSvc: init_session(user_id, query)
    MemSvc->>MemMgr: create_short_term()
    MemMgr->>Cache: set()
    
    UseCase->>MemSvc: enrich_agent_context(query)
    MemSvc->>MemMgr: search(query, top_k=8)
    
    MemMgr->>VStore: search(embedding, user_filter)
    VStore-->>MemMgr: Hits [id_1, id_2]
    
    MemMgr->>DB: get_by_id(id_1)
    DB-->>MemMgr: Entity 1
    MemMgr->>DB: update_score(access_count+1)
    
    MemMgr->>MemMgr: Rank by (Similarity + Importance + Recency)
    MemMgr->>MemMgr: Deduplicate (TF-IDF overlap check against RAG context)
    
    MemMgr-->>MemSvc: Enriched context string
    MemSvc-->>UseCase: Initial Agent State (with memory context)
```

## Post-Execution: Episodic Memory Persistence

Once the LangGraph workflow successfully completes and generates an answer, the trace is saved as an episodic memory.

```mermaid
sequenceDiagram
    participant UseCase as ExecuteAgentWorkflowUseCase
    participant Graph as LangGraph Engine
    participant MemSvc as MemoryService
    participant MemMgr as MemoryManager
    participant VStore as QdrantVectorStore
    participant DB as PostgresRepository

    UseCase->>Graph: ainvoke(Initial State)
    Graph-->>UseCase: Final State (answer, trace, confidence)
    
    UseCase->>MemSvc: save_episode(query, final_answer, trace)
    MemSvc->>MemSvc: distil_lessons(agent_outputs)
    
    MemSvc->>MemMgr: create_episodic(EpisodicMemory entity)
    MemMgr->>DB: save()
    DB-->>MemMgr: saved entity (with new ID)
    
    MemMgr->>MemMgr: embed(query + answer + lessons)
    MemMgr->>VStore: upsert(embedding, metadata)
    
    MemMgr-->>MemSvc: Success
    MemSvc-->>UseCase: Success
```
