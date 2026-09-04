# Repository & Project Management API Documentation

This document describes the REST APIs for Repository and Project Management (Phase 10.4).

All endpoints require a valid `Authorization: Bearer <token>` header.
Users can only access their own repositories and projects.

---

## Repositories API

### `GET /api/v1/repositories`
List repositories owned by the user.

**Query Parameters:**
- `workspace_id`: (optional) Filter by workspace ID
- `provider`: (optional) `github` | `gitlab` | `bitbucket` | `local`
- `indexing_status`: (optional) `pending` | `indexing` | `indexed` | `failed`
- `search`: (optional) Substring search on name, description, owner, URL
- `skip`, `limit`, `sort_by`, `sort_dir`

---

### `POST /api/v1/repositories/import`
Import a repository and run AI stack detection.

**Request Body:**
```json
{
  "url": "https://github.com/owner/repository",
  "provider": "github",
  "name": "my-repo",
  "description": "Optional description",
  "default_branch": "main",
  "workspace_id": "optional-uuid",
  "git_access_token": "optional-pat-token"
}
```

---

### `GET /api/v1/repositories/{repo_id}`
Retrieve repository details.

---

### `PUT /api/v1/repositories/{repo_id}`
Update repository metadata.

---

### `DELETE /api/v1/repositories/{repo_id}`
Delete a repository.

---

### `POST /api/v1/repositories/{repo_id}/refresh`
Re-run stack detection and trigger index refresh.

---

### `GET /api/v1/repositories/{repo_id}/health`
Perform connectivity health check.

---

### `GET /api/v1/repositories/{repo_id}/branches`
List available branches.

---

### `PATCH /api/v1/repositories/{repo_id}/branch`
Switch active branch.

---

## Projects API

### `GET /api/v1/projects`
List projects.

---

### `POST /api/v1/projects`
Create a new project container.

---

### `GET /api/v1/projects/{project_id}`
Get project details and linked repositories.

---

### `PUT /api/v1/projects/{project_id}`
Update project title/description.

---

### `POST /api/v1/projects/{project_id}/archive`
Archive a project.

---

### `DELETE /api/v1/projects/{project_id}`
Delete a project.

---

### `POST /api/v1/projects/{project_id}/repositories/{repo_id}`
Link a repository to a project.

---

### `DELETE /api/v1/projects/{project_id}/repositories/{repo_id}`
Unlink a repository from a project.

---

### `GET /api/v1/projects/{project_id}/dashboard`
Get project-level aggregate metrics dashboard.
