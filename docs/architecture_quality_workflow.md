# AI Architecture & Code Quality Agent Workflow

## Overview

The **AI Architecture & Code Quality Agent** (Phase 11.5) provides enterprise-grade evaluation of repository health, architectural integrity, Clean Architecture compliance, layer dependency violations, module coupling/cohesion, SOLID principles, design pattern opportunities, documentation coverage, and long-term technical debt.

> [!IMPORTANT]
> The Architecture & Code Quality Agent is **strictly advisory**. It **NEVER** modifies source code automatically. It generates actionable recommendations, repository-wide scores, layer violation maps, and complexity hotspot lists.

---

## LangGraph Multi-Agent Workflow Sequence

```
Repository Analysis
       │
       ▼
   RAG Context
       │
       ▼
Memory Retrieval
       │
       ▼
  Code Review
       │
       ▼
Security Analysis
       │
       ▼
Performance Analysis
       │
       ▼
Refactoring Analysis
       │
       ▼
Architecture & Quality Analysis  ◄── (Phase 11.5: Consumes all prior findings)
       │
       ▼
Final Review Report
```

---

## Analysis Scope

### 1. Architecture
- **Clean Architecture Compliance**: Verifies that inner domain layers have no outward dependencies on infrastructure, UI, or frameworks.
- **Layer Dependency Violations**: Flags direct imports from domain entities into database driver adapters or persistence layers.
- **Circular Dependencies**: Identifies package/module cycles.
- **Module Coupling & Cohesion**: Measures inter-module dependency density and single-responsibility cohesion.
- **Package & Repo Organization**: Evaluates folder structures, component placement, and microservice boundaries.

### 2. Maintainability
- **Maintainability Index & Tech Debt**: Calculates health scores and technical debt hours.
- **Code Duplication & Complexity Hotspots**: Identifies high-risk files requiring structural refactoring.
- **Dead Code & Unused Imports/Variables**: Detects leftover boilerplate or unreferenced code symbols.
- **Documentation Coverage**: Evaluates docstring completeness and module-level summaries.

### 3. Design Principles
- **SOLID Violations**: Identifies Single Responsibility, Open-Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion breaches.
- **Design Pattern Opportunities**: Recommends Abstract Factory, Strategy, Observer, Decorator, or Repository pattern applications.
- **Separation of Concerns & Encapsulation**: Flags leaked implementation details or excessive public state mutation.

---

## Output Schema

Each output includes:

```json
{
  "findings": [
    {
      "category": "clean_architecture",
      "severity": "high",
      "priority": "high",
      "file_path": "src/domain/entities/user.py",
      "line_number": 15,
      "explanation": "Domain model directly imports SQLAlchemy ORM infrastructure model.",
      "root_cause": "Domain layer tightly coupled with persistence driver.",
      "business_impact": "Prevents switching database drivers or isolated unit testing.",
      "recommendation": "Decouple domain entity from ORM model using mapper interfaces.",
      "estimated_effort_hours": 3.5,
      "confidence_score": 0.95
    }
  ],
  "metrics": {
    "overall_health_score": 85.0,
    "architecture_score": 88.0,
    "maintainability_score": 80.0,
    "technical_debt_score": 78.0,
    "complexity_score": 82.0,
    "documentation_score": 85.0,
    "modularity_score": 84.0,
    "testability_score": 86.0
  },
  "dependency_analysis": {
    "layer_violations": [
      {
        "source_layer": "domain",
        "target_layer": "infrastructure",
        "source_file": "src/domain/services/user_service.py",
        "target_file": "src/infrastructure/db.py",
        "description": "Domain service imports infrastructure DB helper."
      }
    ],
    "circular_dependencies": [],
    "hotspot_files": [
      {
        "file_path": "src/application/use_cases/review_code.py",
        "complexity_score": 85.0,
        "technical_debt_hours": 12.0,
        "issue_count": 4
      }
    ]
  },
  "summary": "Repository displays solid Clean Architecture patterns with minor layer coupling issues."
}
```

---

## REST API Endpoint

`GET /api/v1/reviews/{review_id}/architecture`

### Response Payload
- `architecture_findings`: Array of architecture & quality finding objects
- `overall_health_score`: Overall repository health score (0-100)
- `architecture_score`: Architecture score (0-100)
- `maintainability_score`: Maintainability score (0-100)
- `technical_debt_score`: Technical debt score (0-100)
- `complexity_score`: Complexity score (0-100)
- `documentation_score`: Documentation score (0-100)
- `modularity_score`: Modularity score (0-100)
- `testability_score`: Testability score (0-100)
- `dependency_analysis`: Layer violations, circular dependencies, hotspot files

---

## Frontend Architecture Tab Features

1. **8-Metric Repository Health Dashboard**: Circular Overall Health gauge alongside 7 metric indicator rings (Architecture, Maintainability, Tech Debt, Complexity, Documentation, Modularity, Testability).
2. **Clean Architecture Layer Violations Table**: Highlights direct imports violating Clean Architecture boundaries.
3. **Hotspot Files & File Rankings**: Ranks files by complexity score, technical debt hours, and issue count.
4. **Interactive Findings List**: Search, Category & Severity filters, Sorting by Severity/Effort/Confidence/File, Pagination (10 per page), and Expandable Card Details (Root Cause, Business Impact, Recommendation, Estimated Effort, Confidence).
