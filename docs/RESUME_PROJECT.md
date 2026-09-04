# KAI Code Studio — Resume Project Specifications

Professional resume entries, project summary bullets, and verified technical highlights for software engineering resumes and portfolio profiles.

---

## 📌 A) One-Line Summary

> Engineered **KAI Code Studio**, an enterprise multi-agent software engineering platform built with **React 19**, **FastAPI**, **LangGraph**, and **Qdrant** featuring AST-aware repository RAG, multi-agent code reviews, static fix verification, and automated GitHub PR workflows.

---

## 📋 B) 3-Bullet Resume Version

- **Multi-Agent Orchestration & RAG**: Built a stateful multi-agent system (Supervisor, Planner, Evaluator, Specialized Agents) using **LangGraph** and **Qdrant** hybrid retrieval with AST-aware chunking and 6-signal re-ranking across multi-language codebases.
- **Security & OAuth Architecture**: Implemented server-side AES-128-CBC (`Fernet`) encrypted GitHub OAuth token storage, ensuring strict per-user credential isolation across API routes, tool adapters, and automated PR generation workflows.
- **Automated Fix-to-PR Workflow**: Designed an automated code review engine featuring unified diff generation, static AST verification, isolated test sandboxing, and direct GitHub branch-to-PR creation.

---

## 🛠️ C) 4-Bullet Technical Version

- **Architected Clean Architecture Monorepo**: Designed a modular **FastAPI** + **React 19** application separating domain logic, application use cases, infrastructure adapters (PostgreSQL, Redis, Qdrant), and FastAPI REST interfaces.
- **High-Performance Hybrid Vector Search**: Constructed an AST-aware structural chunking pipeline using SentenceTransformers (`all-MiniLM-L6-v2`) and **Qdrant** vector store with 6-signal re-ranking (recency, file distance, score, structural match, query overlap, depth).
- **Enterprise Security & Isolation**: Applied path traversal safeguards (`shell=False` git commands), strict `user_id` multi-tenant data boundaries, encrypted memory stores, and zero secret exposure across frontend build bundles.
- **DevOps & Production Dockerization**: Configured full **Docker Compose** production stack with Nginx SPA reverse proxy, health-checked container dependencies, and automated **GitHub Actions CI** test workflows.

---

## 💻 D) Tech Stack Line

**Languages & Frameworks**: Python 3.11, TypeScript, React 19, FastAPI, LangGraph, Pydantic v2  
**Databases & AI**: PostgreSQL 15, Redis 7, Qdrant Vector DB, SentenceTransformers, Google Gemini / OpenAI GPT-4o  
**DevOps & Tools**: Docker, Docker Compose, Nginx, GitHub Actions CI, Git OAuth API, Vite, Vitest, Pytest  

---

## 📊 Verified Technical Metrics

- **Backend Test Suite**: 566 unit/integration tests passing (100% pass rate).
- **Frontend Test Suite**: 182 unit/component tests passing across 15 test suites.
- **Production Build**: Clean TypeScript compilation (`tsc -b`) and Vite production bundle generation in ~4.95 seconds.
- **Security Coverage**: 41 dedicated cross-user isolation and security tests verifying encrypted OAuth storage and multi-tenant data boundaries.
