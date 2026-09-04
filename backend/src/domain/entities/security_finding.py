from pydantic import BaseModel, Field
from enum import Enum

class SeverityEnum(str, Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'

class SecurityFinding(BaseModel):
    vulnerability: str = Field(..., description='Name of the vulnerability')
    severity: SeverityEnum = Field(..., description='Severity level')
    cwe_id: str = Field(..., description='CWE identifier')
    owasp_category: str = Field(..., description='OWASP category')
    file_path: str = Field(..., description='File where issue was found')
    line_number: int = Field(..., description='Line number of the issue')
    explanation: str = Field(..., description='Detailed explanation of the issue')
    attack_scenario: str = Field(..., description='Possible attack scenario')
    suggested_fix: str = Field(..., description='Recommended fix')
    confidence: float = Field(..., description='Confidence score between 0 and 1')
