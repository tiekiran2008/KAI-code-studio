# KAI Code Studio — System Architecture Documentation

Detailed technical specification of KAI Code Studio's Clean Architecture, multi-agent orchestration, RAG engine, memory system, GitHub OAuth security, and infrastructure setup.

---

## 🏗️ 1. Overall System Architecture

KAI Code Studio adheres strictly to **Clean Architecture** principles, decoupling business domain logic from framework dependencies, database persistence, and external AI providers.

```mermaid
graph TB
    subgraph ClientLayer ["Client Layer"]
        ReactApp["React 19 + TypeScript (Vite)"]
        ZustandStores["Zustand Global State Stores"]
        AxiosClient["Axios REST API Client"]
    end

    subgraph InterfaceLayer ["Interfaces & Delivery Layer"]
        FastAPIApp["FastAPI REST Application (src/interfaces/api)"]
        APIRouters["V1 Routers (auth, repos, reviews, integrations, rag)"]
        DependencyInjection["Request-Scoped DI (dependencies.py)"]
    end

    subgraph ApplicationLayer ["Application Use Cases & Services"]
        IngestionService["Repository Ingestion Service"]
        RAGService["RAG Pipeline Service"]
        ReviewService["Code Review Service"]
        FixService["Fix-to-PR Workflow Service"]
        GitHubService["GitHub Integration Service"]
    end

    subgraph DomainLayer ["Domain Layer (Business Entities & Contracts)"]
        DomainModels["Entities (Repository, Review, Finding, User)"]
        RepoInterfaces["Repository Interfaces (Abstractions)"]
        ToolRegistry["Tool Registry & Adapters Interface"]
    end

    subgraph InfraLayer ["Infrastructure & External Adapters"]
        LangGraphEngine["LangGraph Multi-Agent Engine"]
        QdrantAdapter["Qdrant Vector Adapter"]
        PostgresDB["PostgreSQL / SQLAlchemy Persistence"]
        RedisStore["Redis Session & Cache Store"]
        GitHubAdapter["GitHub API & OAuth Adapter"]
    end

    ClientLayer --> InterfaceLayer
    InterfaceLayer --> ApplicationLayer
    ApplicationLayer --> DomainLayer
    ApplicationLayer --> InfraLayer
    InfraLayer --> DomainLayer
```

---

## 🤖 2. LangGraph Multi-Agent Engine

The multi-agent execution pipeline is built on **LangGraph**, executing state-bound graph traversals with supervisor routing, evaluations, and recursion controls.

```mermaid
stateDiagram-v2
    [*] --> Supervisor
    Supervisor --> Planner: Complex Engineering Request
    Planner --> SecurityAgent: Audit Vulnerabilities
    Planner --> PerformanceAgent: Analyze Bottlenecks
    Planner --> QualityAgent: Structural & Architecture Check
    
    SecurityAgent --> Evaluator
    PerformanceAgent --> Evaluator
    QualityAgent --> Evaluator
    
    Evaluator --> Supervisor: Score < Threshold (Retry Loop)
    Evaluator --> [*]: Score >= Threshold (Finalized Output)
```

### Agent Responsibilities

| Component | Class / Service | Function |
| :--- | :--- | :--- |
| **Supervisor Agent** | `SupervisorAgent` | Inspects task input, delegates execution to sub-agents, aggregates state. |
| **Planner Agent** | `PlannerAgent` | Generates execution plans for multi-step engineering tasks. |
| **Security Agent** | `SecurityAgent` | Scans source files for security vulnerabilities (injection, hardcoded keys, traversal). |
| **Performance Agent** | `PerformanceAgent` | Analyzes execution complexity ($O(n)$ bounds), database queries, and async IO. |
| **Quality Agent** | `QualityAgent` | Evaluates SOLID principles, module cohesion, coupling, and docstrings. |
| **Evaluator Agent** | `EvaluatorAgent` | Scores synthesized agent responses (`0.0 - 1.0`), enforcing retry policies. |

---

## 🔍 3. AST-Aware RAG Pipeline & Retrieval

The RAG pipeline provides hybrid vector retrieval with structural re-ranking and grounded citation generation.

```mermaid
sequenceDiagram
    participant User as Developer / UI
    participant RAG as RAG Service
    participant Embed as SentenceTransformer
    participant Qdrant as Qdrant Vector DB
    participant Rank as 6-Signal Re-Ranker
    participant LLM as Gemini / LLM

    User->>RAG: Query ("How is JWT authentication configured?")
    RAG->>Embed: Embed Query Vector (384-dim)
    Embed-->>RAG: Query Vector
    RAG->>Qdrant: Hybrid Vector + Keyword Search (user_id scoped)
    Qdrant-->>RAG: Raw Chunks (Top 20)
    RAG->>Rank: Re-Rank Chunks (recency, file dist, score, AST match, overlap, depth)
    Rank-->>RAG: Top K Chunks (Top 8)
    RAG->>LLM: Synthesize Grounded Response with Chunks
    LLM-->>RAG: Grounded Response + Citations
    RAG-->>User: Final Answer with Line-Range Citations
```

---

## 🧠 4. Tiered Memory Architecture

1. **Short-Term Session Memory**: Ephemeral conversation history stored in **Redis** with configurable TTL (`1800s`).
2. **Long-Term Operational Memory**: Review metadata, findings, user profiles, and workspace settings persisted in **PostgreSQL**.
3. **Semantic Code Memory**: Cross-session code patterns, past review findings, and codebase context indexed in **Qdrant**.

---

## 🔐 5. Security & Isolation Boundaries

- **OAuth Encryption**: GitHub access tokens are encrypted at rest using AES-128-CBC (`Fernet`) before persistence in PostgreSQL.
- **Per-User Dependency Injection**: FastAPI dependencies inject the active user's OAuth token dynamically into request-scoped adapters (`GitHubToolAdapter`, `GitHubPullRequestService`).
- **Multi-Tenant Scoping**: All vector collections and SQL tables enforce `user_id` filtering on read/write operations.
- **Process Protection**: Git commands execute via explicit argument vectors (`shell=False`) avoiding shell expansion vulnerabilities.
