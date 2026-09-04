# KAI Code Studio — 3-5 Minute Demo Guide

A step-by-step presentation script designed for portfolio walkthroughs and technical interviews.

---

## ⏱️ Timeline & Flow Overview

```
[0:00 - 0:45] 1. Introduction & Authentication
[0:45 - 1:30] 2. Repository Ingestion & Structural RAG
[1:30 - 2:30] 3. Multi-Agent Code Review & Findings
[2:30 - 3:30] 4. Fix Generation, Static Verification & GitHub PR
[3:30 - 4:15] 5. Intelligent Tiered Memory & Architecture Highlights
```

---

## 🎬 Detailed Step-by-Step Script

### Step 1: Introduction & Authentication (0:00 - 0:45)
- **Action**: Open the application at `http://localhost:5173`. Show the Dashboard page.
- **What to SAY**:
  > *"Welcome to KAI Code Studio. Traditional AI coding tools act as simple prompt wrappers that lack full codebase understanding and automated git workflows. KAI Code Studio is an autonomous multi-agent platform designed to ingest enterprise codebases, analyze architecture and security vulnerabilities, verify fixes, and automate pull requests."*
- **Action**: Show the Settings page with connected GitHub status.
- **What to SAY**:
  > *"The platform integrates with GitHub OAuth. Access tokens are stored on the server using AES-128-CBC authenticated encryption, ensuring credentials never leak to the client or cross user boundaries."*

---

### Step 2: Repository Ingestion & Structural RAG (0:45 - 1:30)
- **Action**: Navigate to **Repositories** and click **Import Repository**.
- **What to SAY**:
  > *"When a repository is imported, our ingestion engine scans source files, ignoring binary, dependency, and environment files. It parses code using AST-aware chunking for Python and structural splitters for other languages, generating embeddings via SentenceTransformers into Qdrant vector database."*
- **Action**: Open **Repository Details** and type a code query in the search bar.
- **What to SAY**:
  > *"When querying the codebase, our hybrid retriever combines Qdrant vector similarity with keyword matching, passed through a 6-signal re-ranker. Responses are strictly grounded with exact file paths and line ranges."*

---

### Step 3: Multi-Agent Code Review (1:30 - 2:30)
- **Action**: Go to **Code Review**, select a repository, and click **Start Review**.
- **What to SAY**:
  > *"Under the hood, KAI Code Studio uses a LangGraph multi-agent graph. A Supervisor routes execution to specialized agents: Security audits OWASP risks, Performance inspects bottlenecks, Quality verifies clean architecture, and Refactoring proposes improvements. An Evaluator agent score-checks results against confidence thresholds before finalizing."*
- **Action**: Show the **Review Results** page. Point out finding cards (Severity, File Path, Explanation, Recommendation).
- **What to SAY**:
  > *"The review output categorizes findings by severity, pointing to exact file locations with actionable remediation steps."*

---

### Step 4: Fix Generation, Verification & GitHub PR (2:30 - 3:30)
- **Action**: Click **Generate Fix** on a finding. Open the **Fix Modal**.
- **What to SAY**:
  > *"KAI Code Studio generates unified code diffs for findings. Before applying, developers can run Static AST Verification to ensure syntax correctness, and Isolated Test Verification to validate against test suites."*
- **Action**: Click **Create Pull Request** (or show the PR modal).
- **What to SAY**:
  > *"Once verified, KAI commits the fix to an isolated feature branch, pushes to GitHub, and opens a pull request using the developer's connected OAuth credentials—closing the loop from finding to pull request."*

---

### Step 5: Memory & Architecture Highlights (3:30 - 4:15)
- **Action**: Navigate to **Memory Center** or show the Architecture diagram in `docs/ARCHITECTURE.md`.
- **What to SAY**:
  > *"Finally, KAI incorporates tiered intelligent memory—Redis for active session state, PostgreSQL for long-term review metrics, and Qdrant for semantic code memory. The entire application follows Clean Architecture in FastAPI and React 19, fully containerized with Docker Compose."*
