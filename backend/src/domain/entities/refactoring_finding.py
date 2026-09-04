from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List


class RefactoringSeverityEnum(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RefactoringCategoryEnum(str, Enum):
    COMPLEXITY = "complexity"
    DUPLICATION = "duplication"
    NAMING = "naming"
    COUPLING = "coupling"
    COHESION = "cohesion"
    SOLID = "solid"
    PATTERNS = "patterns"
    DEAD_CODE = "dead_code"
    STRUCTURE = "structure"
    ERROR_HANDLING = "error_handling"
    ASYNC = "async"
    GOD_OBJECT = "god_object"
    FEATURE_ENVY = "feature_envy"
    SMELLS = "smells"


class RefactoringFinding(BaseModel):
    refactoring_type: str
    priority: RefactoringSeverityEnum
    category: RefactoringCategoryEnum
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    explanation: str
    current_problem: Optional[str] = None
    suggested_refactoring: Optional[str] = None
    before_preview: Optional[str] = None
    after_preview: Optional[str] = None
    benefits: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    estimated_effort_hours: float = 0.0
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


class RefactoringMetrics(BaseModel):
    overall_priority: Optional[RefactoringSeverityEnum] = None
    estimated_total_effort_hours: float = 0.0
    estimated_maintainability_improvement: float = 0.0
    estimated_technical_debt_reduction: float = 0.0
    estimated_complexity_reduction: float = 0.0
