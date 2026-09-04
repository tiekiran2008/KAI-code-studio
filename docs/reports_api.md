# Engineering Reports API Specification

Base Path: `/api/v1/reports`

All endpoints require authentication (`Authorization: Bearer <token>`).

---

## Endpoints Summary

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/reports/generate` | Generate a report from an existing code review or repository |
| `GET` | `/api/v1/reports` | List all reports for the authenticated user |
| `GET` | `/api/v1/reports/{report_id}` | Get report details by ID |
| `DELETE` | `/api/v1/reports/{report_id}` | Delete a report by ID |
| `GET` | `/api/v1/reports/{report_id}/export` | Export a report in PDF, HTML, Markdown, JSON, or SARIF format |
| `POST` | `/api/v1/reports/compare` | Compare two historical reports side-by-side |

---

## Endpoint Details

### 1. Generate Report
**`POST /api/v1/reports/generate`**

**Request Body:**
```json
{
  "repository_id": "repo-123",
  "review_id": "rev-456",
  "title": "Q3 Architecture & Security Audit"
}
```

**Response (200 OK):**
```json
{
  "id": "rpt-789",
  "repository_id": "repo-123",
  "review_id": "rev-456",
  "user_id": "user-001",
  "title": "Q3 Architecture & Security Audit",
  "version": "1.0",
  "status": "completed",
  "overall_health_score": 78.5,
  "risk_score": 21.5,
  "security_score": 82.0,
  "performance_score": 75.0,
  "architecture_score": 80.0,
  "maintainability_score": 76.0,
  "technical_debt_score": 72.0,
  "complexity_score": 84.0,
  "documentation_score": 88.0,
  "testability_score": 81.0,
  "repository_snapshot": {
    "repository_id": "repo-123"
  },
  "export_formats": [],
  "report_content": { ... },
  "created_at": "2026-08-05T14:30:00Z",
  "updated_at": null
}
```

---

### 2. List Reports
**`GET /api/v1/reports?skip=0&limit=50`**

**Response (200 OK):** Array of report objects.

---

### 3. Get Report Details
**`GET /api/v1/reports/{report_id}`**

**Response (200 OK):** Single report object.

---

### 4. Delete Report
**`DELETE /api/v1/reports/{report_id}`**

**Response (204 No Content)**

---

### 5. Export Report
**`GET /api/v1/reports/{report_id}/export?format=markdown`**

**Query Parameters:**
- `format`: `markdown` | `html` | `json` | `sarif` | `pdf` (default: `markdown`)

**Response:** File download matching requested content-type.
- `markdown` → `text/markdown`
- `html` → `text/html`
- `json` → `application/json`
- `sarif` → `application/sarif+json`
- `pdf` → `application/pdf`

---

### 6. Side-by-Side Report Comparison
**`POST /api/v1/reports/compare`**

**Request Body:**
```json
{
  "report_id_a": "rpt-001",
  "report_id_b": "rpt-002"
}
```

**Response (200 OK):**
```json
{
  "report_a": { "id": "rpt-001", "created_at": "...", "scores": { ... }, "finding_counts": { ... } },
  "report_b": { "id": "rpt-002", "created_at": "...", "scores": { ... }, "finding_counts": { ... } },
  "score_deltas": {
    "overall_health_score": +5.5,
    "security_score": +10.0,
    "risk_score": -5.5
  },
  "finding_count_deltas": {
    "security": -2,
    "code_review": -5
  },
  "improved_metrics": ["overall_health_score", "security_score"],
  "degraded_metrics": []
}
```
