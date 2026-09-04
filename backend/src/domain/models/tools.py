"""
Tool Framework Domain Models
============================
Defines the core entities and enums for the tool calling framework.
Includes standard schemas for metadata, permissions, and results.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class PermissionLevel(str, Enum):
    """Role-based access control levels for tool execution."""
    READ_ONLY = "read_only"
    RESTRICTED = "restricted"
    ADMIN_ONLY = "admin_only"


@dataclass
class ToolMetadata:
    """Metadata detailing the capabilities and constraints of a tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]  # JSON Schema format
    output_schema: Dict[str, Any] # JSON Schema format
    permissions: PermissionLevel
    timeout_seconds: float = 30.0
    retry_policy: Dict[str, Any] = field(default_factory=lambda: {"max_retries": 1, "backoff_factor": 2.0})
    version: str = "1.0.0"


@dataclass
class ToolResult:
    """Standardized output wrapper for all tool executions."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
