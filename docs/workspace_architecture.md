# Workspace Architecture

## Overview

The Workspace module provides isolated engineering environments that act as top-level organizational containers for repositories, AI model configurations, and tool settings.

## Entity Relationship

```
User (Supabase Auth)
 └── Workspaces (1:N)
      ├── Repositories (1:N)
      │    ├── Source Files
      │    │    └── Code Symbols
      │    ├── Memories (Phase 7)
      │    └── RAG Sessions (Phase 5)
      ├── AI Configuration (inline)
      └── Tool/Env Config (inline, tool_config JSON)
```

## Database Schema

### `workspaces` table

| Column | Type | Description |
|--------|------|-------------|
| `id` | `VARCHAR` (UUID) | Primary key |
| `user_id` | `VARCHAR` | Owner's Supabase auth ID, indexed |
| `name` | `VARCHAR` | Display name (1–100 chars) |
| `description` | `TEXT` | Optional description |
| `default_ai_model` | `VARCHAR` | e.g., `gpt-4o`, `claude-3-5-sonnet` |
| `default_repo_id` | `VARCHAR` (FK) | Optional default repository |
| `vector_db_config` | `JSONB` | Qdrant/vector DB settings override |
| `tool_config` | `JSONB` | Tool flags + env variable secrets |
| `created_at` | `TIMESTAMPTZ` | Auto-set by server |
| `updated_at` | `TIMESTAMPTZ` | Auto-updated on write |

### Modified: `repositories` table

| Column (added) | Type | Description |
|----------------|------|-------------|
| `workspace_id` | `VARCHAR` (FK → `workspaces.id`) | Parent workspace. `ON DELETE CASCADE`. Nullable for backward compatibility. |

## Clean Architecture Layers

```
┌──────────────────────────────────────────────────┐
│  Interface Layer (FastAPI)                        │
│  src/interfaces/api/v1/workspaces.py              │
│  • 5 REST endpoints (CRUD + list)                 │
│  • Auth via get_current_user dependency           │
│  • Pydantic response models                       │
├──────────────────────────────────────────────────┤
│  Application Layer (Services)                     │
│  src/application/services/workspace_service.py    │
│  • Ownership validation on every operation        │
│  • Business rules (repo_count, defaults)          │
│  • Maps DB models → Domain entities               │
├──────────────────────────────────────────────────┤
│  Infrastructure Layer (Repositories + ORM)        │
│  src/infrastructure/repositories/                 │
│    workspace_repository.py                        │
│  src/infrastructure/persistence/                  │
│    workspace_models.py  (DBWorkspace ORM)         │
│    base.py              (shared declarative Base) │
├──────────────────────────────────────────────────┤
│  Domain Layer (Entities)                          │
│  src/domain/entities/workspace.py                 │
│  • Workspace          (full read model)           │
│  • WorkspaceCreate    (POST body)                 │
│  • WorkspaceUpdate    (PUT body, all-optional)    │
└──────────────────────────────────────────────────┘
```

## Security Model

- Every CRUD endpoint requires a valid Bearer token (`get_current_user` dependency).
- The `user_id` is **never** accepted from the client body — it is always extracted from the authenticated JWT `sub` claim.
- The service layer validates ownership on **every** read, update, and delete by comparing `db_workspace.user_id == user_id` before executing any mutation.
- Attempting to access or mutate another user's workspace returns `None` → 404 (not 403, to avoid information leakage about workspace existence).

## Frontend Architecture

```
src/
├── api/
│   └── workspaces.ts          # HTTP client methods (fetchClient wrappers)
├── store/
│   └── workspaceStore.ts      # Zustand store with persist middleware
│                               # (activeWorkspaceId stored in localStorage)
├── pages/workspaces/
│   ├── WorkspaceListPage.tsx   # Grid list with search, sort, pagination
│   ├── WorkspaceCreatePage.tsx # Create form with validation
│   └── WorkspaceSettingsPage.tsx # Edit + danger zone delete
└── components/
    └── workspace/
        └── WorkspaceSwitcher.tsx # Dropdown switcher in TopNavbar
```

## Workspace Switcher

The `WorkspaceSwitcher` component is rendered in the `TopNavbar` header (between the page title and the search bar). It:
1. Fetches all user workspaces on mount.
2. Highlights the currently active workspace with a checkmark.
3. Clicking a workspace calls `setActiveWorkspace(id)` (persisted to localStorage).
4. Provides quick-access links to create a new workspace or manage all workspaces.
