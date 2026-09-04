# Code Review Architecture

## System Components

### 1. API Layer
Exposes REST endpoints (`/api/v1/reviews/*`) to start and fetch reviews, performance metrics, and refactoring analysis. Utilises FastAPI for high performance.

### 2. Service Layer
The `CodeReviewService` coordinates the workflow, interacting with the underlying Agent Execution engine and LLM providers to process source code statically and dynamically.

### 3. Agent Execution Engine
The `ExecuteAgentWorkflowUseCase` runs the multi-agent StateGraph review logic using LangGraph. The pipeline executes specialized agents in sequence:
1. **Code Review Agent**: Quality, readability, SOLID principles, cyclomatic complexity.
2. **Security Review Agent**: Vulnerability scanning, CWE/OWASP classification.
3. **Performance Agent**: Algorithmic complexity, memory allocations, N+1 queries.
4. **Refactoring Analysis Agent (Phase 11.4)**: Synthesizes code, security, and performance findings to generate non-destructive refactoring recommendations.

> [!NOTE]
> The Refactoring Agent **never** modifies code automatically; it strictly outputs actionable recommendations, before/after previews, benefits, risks, and maintainability improvement scores.

### 4. Data Persistence
Review data, including detailed findings, performance statistics, and refactoring recommendations, are stored in PostgreSQL using SQLAlchemy (`DBCodeReview` model).

### 5. Frontend Presentation
The React-based frontend fetches review data and presents it using specialised components. The `ReviewResultsPage` breaks down findings into Code Quality, Security, Performance, and Refactoring tabs for intuitive analysis.
