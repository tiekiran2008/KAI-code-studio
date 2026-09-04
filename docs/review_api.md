# Code Review API Documentation

## Endpoints

### 1. Start a Review
`POST /api/v1/reviews/start`
Initiates a new code review for a given repository.
**Body:**
```json
{
  "repository_id": "string",
  "files": ["string"]
}
```
**Response:** `200 OK`
```json
{
  "message": "Review started",
  "review_id": "string"
}
```

### 2. Get Review Status/Results
`GET /api/v1/reviews/{review_id}`
Retrieves the details and general findings of a code review.
**Response:** `200 OK` (CodeReview object)

### 3. Get Review History
`GET /api/v1/reviews/history/{repository_id}?skip=0&limit=50`
Fetches a paginated history of reviews for a repository.

### 4. Get Performance Data
`GET /api/v1/reviews/{review_id}/performance`
Fetches the performance analysis specific data for a review, including performance scores, CPU/memory savings, and findings.
**Response:** `200 OK` (PerformanceData object)

### 5. Get Refactoring Data (Phase 11.4)
`GET /api/v1/reviews/{review_id}/refactoring`
Fetches refactoring recommendations, estimated effort, maintainability improvement score, technical debt reduction, complexity reduction, benefits, and risks for a completed review.
**Response:** `200 OK`
```json
{
  "refactoring_findings": [
    {
      "refactoring_type": "Extract Method",
      "priority": "high",
      "category": "complexity",
      "file_path": "src/main.py",
      "line_number": 42,
      "explanation": "Function process_data is too long and complex.",
      "current_problem": "High nesting in process_data function",
      "suggested_refactoring": "Extract inner loop into separate function",
      "before_preview": "def process_data(): ...",
      "after_preview": "def process_data(): helper()",
      "benefits": ["Reduced complexity"],
      "risks": ["Minor indirection"],
      "estimated_effort_hours": 2.0,
      "confidence_score": 0.95
    }
  ],
  "refactoring_priority": "high",
  "estimated_refactoring_effort": 2.0,
  "estimated_maintainability_improvement": 25.0,
  "estimated_technical_debt_reduction": 3.0,
  "estimated_complexity_reduction": 30.0
}
```

### 6. Get Architecture & Code Quality Data (Phase 11.5)
`GET /api/v1/reviews/{review_id}/architecture`
Fetches Clean Architecture findings, overall repository health metrics, layer dependency violations, and hotspot file analysis.
**Response:** `200 OK`
```json
{
  "architecture_findings": [
    {
      "category": "clean_architecture",
      "severity": "high",
      "priority": "high",
      "file_path": "src/domain/user.py",
      "line_number": 15,
      "explanation": "Domain entity directly imports ORM model.",
      "root_cause": "Coupling domain layer to persistence implementation.",
      "business_impact": "High testing friction.",
      "recommendation": "Decouple domain model using interface.",
      "estimated_effort_hours": 3.5,
      "confidence_score": 0.95
    }
  ],
  "overall_health_score": 85.0,
  "architecture_score": 88.0,
  "maintainability_score": 80.0,
  "technical_debt_score": 78.0,
  "complexity_score": 82.0,
  "documentation_score": 85.0,
  "modularity_score": 84.0,
  "testability_score": 86.0,
  "dependency_analysis": {
    "layer_violations": [],
    "circular_dependencies": [],
    "hotspot_files": []
  }
}
```

