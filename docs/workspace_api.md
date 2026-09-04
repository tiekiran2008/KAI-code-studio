# Workspace API Documentation

This document describes the Workspace Management REST API (Phase 10.3).

All endpoints require a valid `Authorization: Bearer <token>` header.
Users can only access their own workspaces — ownership is enforced server-side on every request.

---

## Data Model

```json
{
  "id": "string (UUID)",
  "user_id": "string (Supabase Auth ID)",
  "name": "string",
  "description": "string | null",
  "default_ai_model": "string (e.g. gpt-4o)",
  "default_repo_id": "string | null",
  "vector_db_config": "object",
  "tool_config": "object",
  "repo_count": "integer",
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime"
}
```

---

## Endpoints

### `GET /api/v1/workspaces`
List all workspaces owned by the authenticated user.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `skip` | `int` | `0` | Pagination offset |
| `limit` | `int` | `100` | Max results |

**Success (200):** Array of Workspace objects.

**Example:**
```json
[
  {
    "id": "b3f2a1c0-...",
    "user_id": "auth-user-id",
    "name": "Backend API",
    "description": "Main backend services workspace",
    "default_ai_model": "gpt-4o",
    "default_repo_id": null,
    "vector_db_config": {},
    "tool_config": {},
    "repo_count": 3,
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-06-20T14:22:00Z"
  }
]
```

---

### `POST /api/v1/workspaces`
Create a new workspace.

**Request Body:**
```json
{
  "name": "Mobile App",
  "description": "iOS and Android development",
  "default_ai_model": "claude-3-5-sonnet-20241022",
  "default_repo_id": null,
  "vector_db_config": {},
  "tool_config": {}
}
```

**Validation:**
- `name` is required, 1–100 characters.
- `default_ai_model` is required.

**Success (201):** The newly created Workspace object.

**Errors:**
- `401 Unauthorized`: Missing or invalid token.
- `422 Unprocessable Entity`: Validation failure.

---

### `GET /api/v1/workspaces/{workspace_id}`
Retrieve a specific workspace by ID.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `workspace_id` | `string` | UUID of the workspace |

**Success (200):** Workspace object.

**Errors:**
- `401 Unauthorized`
- `404 Not Found`: Workspace does not exist or is owned by a different user.

---

### `PUT /api/v1/workspaces/{workspace_id}`
Update an existing workspace. All fields are optional — only provided fields are updated.

**Request Body:**
```json
{
  "name": "Renamed Workspace",
  "default_ai_model": "gemini-1.5-pro",
  "tool_config": {
    "GITHUB_TOKEN": "ghp_..."
  }
}
```

**Success (200):** The fully updated Workspace object.

**Errors:**
- `401 Unauthorized`
- `404 Not Found`: Workspace not found or not owned by the requester.
- `422 Unprocessable Entity`: Validation failure.

---

### `DELETE /api/v1/workspaces/{workspace_id}`
Permanently delete a workspace and all its associated repositories.

> [!CAUTION]
> This is irreversible. All repositories, memories, and conversations inside the workspace will be permanently deleted (cascade).

**Success (204 No Content):** Empty response.

**Errors:**
- `401 Unauthorized`
- `404 Not Found`: Workspace not found or not owned by the requester.
