# Tool Calling Architecture

This document outlines the architecture for Phase 8: Tool Calling Framework.

## Objective
To provide AI agents (specifically the `SupervisorAgent`) with safe, read-only access to external developer environments (GitHub, Local Filesystem, Databases).

## Core Components

### 1. Tool Registry (`src/infrastructure/tools/registry.py`)
- **Responsibility**: In-memory catalog of all available tool adapters.
- **Features**:
  - `register(tool)`: Validates and stores a tool.
  - `get_tool(name)`: Retrieves a specific tool instance.
  - `list_tools(min_permission)`: Lists tools that meet the RBAC requirement of the caller.

### 2. Tool Manager (`src/infrastructure/tools/manager.py`)
- **Responsibility**: Orchestrates tool execution safely.
- **Features**:
  - Validates `PermissionLevel` against the tool's required permissions.
  - Enforces `timeout_seconds` using `asyncio.wait_for`.
  - Implements exponential backoff retries via `retry_policy`.
  - Emits telemetry and observability logs via `ToolMetrics`.

### 3. Tool Adapters (`src/infrastructure/tools/adapters/`)
- Concrete implementations of `ITool`.
- **GitHub**: `httpx` integration for read-only repo data.
- **Local FS**: Sandbox-restricted file reading and glob searching.
- **Docs**: RAG engine hook for documentation search.
- **Database**: Repository metadata and conversational history extraction.
- **Repo Diff**: Safe `subprocess` wrapper for `git diff` commands.

### 4. Supervisor Agent (`src/application/agents/supervisor.py`)
- Retrieves JSON Schemas of authorized tools.
- Feeds schemas into LLM native tool-calling APIs.
- Receives tool execution requests, passes them to `ToolManager`, and loops until all required data is fetched for the final synthesis.
