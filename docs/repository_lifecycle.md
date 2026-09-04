# Repository & Project Lifecycle Architecture

## Repository Ingestion Pipeline

```
Import Request (URL, PAT)
       │
       ▼
1. Validation & Duplicate Check
       │
       ▼
2. Provider & Owner Detection
       │
       ▼
3. StackDetector (AI Heuristic Engine)
       ├─ Primary Language (Python, TypeScript, Go, Rust, Java, etc.)
       ├─ Framework (Next.js, FastAPI, React, Spring Boot, Django)
       ├─ Package Manager (npm, pip, cargo, maven, poetry)
       └─ Test Framework (pytest, jest, JUnit)
       │
       ▼
4. DB Persistence & Initial Status (`indexed`)
       │
       ▼
5. RAG & Memory Integration
       ├─ Code symbol parsing (AST)
       ├─ Vector embedding generation (Qdrant)
       └─ Repository Memory consolidation
```

## Branch Management Lifecycle

- Repositories track both `default_branch` and `current_branch`.
- Switching branch (`PATCH /api/v1/repositories/{id}/branch`) updates `current_branch`.
- RAG queries scoping to a repository automatically restrict vector retrieval to symbols indexed on the current branch.

## Project Aggregation Lifecycle

- Projects act as multi-repo containers.
- Aggregated metrics automatically calculate total chunks, language diversity, and indexing health across all linked repositories.
