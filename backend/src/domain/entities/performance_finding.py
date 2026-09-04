from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional

class PerformanceSeverityEnum(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class PerformanceFinding(BaseModel):
    issue: str
    severity: PerformanceSeverityEnum
    estimated_impact: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    root_cause: Optional[str] = None
    suggested_optimization: Optional[str] = None
    expected_performance_gain: Optional[str] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    cwe_id: Optional[int] = None
    owasp_category: Optional[str] = None
