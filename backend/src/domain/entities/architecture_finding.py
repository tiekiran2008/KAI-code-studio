"""
Architecture & Code Quality Finding Domain Entities
===================================================
Domain models and enums representing architectural findings, Clean Architecture compliance
violations, maintainability issues, design flaws, layer dependencies, and repo-wide health metrics.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


class ArchitectureCategoryEnum(str, Enum):
    ARCHITECTURE = "architecture"
    CLEAN_ARCHITECTURE = "clean_architecture"
    COUPLING = "coupling"
    COHESION = "cohesion"
    SOLID = "solid"
    PATTERNS = "patterns"
    TECHNICAL_DEBT = "technical_debt"
    COMPLEXITY = "complexity"
    DOCUMENTATION = "documentation"
    TESTABILITY = "testability"
    LAYER_VIOLATION = "layer_violation"
    MODULARITY = "modularity"


class ArchitectureSeverityEnum(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ArchitectureFinding:
    category: str
    severity: str
    priority: str
    explanation: str
    root_cause: str
    business_impact: str
    recommendation: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    estimated_effort_hours: float = 1.0
    confidence_score: float = 1.0


@dataclass
class ArchitectureQualityMetrics:
    overall_health_score: float = 100.0
    architecture_score: float = 100.0
    maintainability_score: float = 100.0
    technical_debt_score: float = 100.0
    complexity_score: float = 100.0
    documentation_score: float = 100.0
    modularity_score: float = 100.0
    testability_score: float = 100.0


@dataclass
class LayerDependencyViolation:
    source_layer: str
    target_layer: str
    source_file: str
    target_file: str
    description: str


@dataclass
class HotspotFile:
    file_path: str
    complexity_score: float
    technical_debt_hours: float
    issue_count: int
