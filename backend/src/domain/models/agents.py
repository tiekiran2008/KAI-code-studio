"""
Agent Domain Models & Shared State
===================================
Domain models and TypedDict shared state definitions for the LangGraph
multi-agent software engineering system.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, TypedDict, Annotated
import operator
from datetime import datetime


class AgentType(str, Enum):
    SUPERVISOR = "supervisor"
    PLANNER = "planner"
    CONTEXT = "context"
    CODE_ANALYSIS = "code_analysis"
    BUG_DETECTION = "bug_detection"
    SECURITY_REVIEW = "security_review"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    TEST_GENERATION = "test_generation"
    CODE_REVIEW = "code_review"
    REFACTORING_ANALYSIS = "refactoring_analysis"
    CODE_QUALITY = "code_quality"
    REPORT_GENERATION = "report_generation"
    EVALUATION = "evaluation"


@dataclass
class AgentTask:
    task_id: str
    description: str
    assigned_agent: AgentType
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"  # pending | in_progress | completed | failed
    output: Optional[str] = None


@dataclass
class AgentTaskPlan:
    query: str
    subtasks: List[AgentTask] = field(default_factory=list)
    execution_order: List[List[str]] = field(default_factory=list)  # Groups of parallel task_ids


@dataclass
class AgentOutput:
    agent_type: AgentType
    summary: str
    details: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ---------------------------------------------------------------------------
# LangGraph Shared State
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    """
    Shared state schema passed across all nodes in the LangGraph graph.
    """
    query: str
    repo_id: str
    session_id: Optional[str]
    
    # Task plan
    plan: Optional[Dict[str, Any]]
    pending_tasks: List[str]
    completed_tasks: List[str]
    
    # Retrieved repository context
    retrieved_context: str
    retrieved_chunks: List[Dict[str, Any]]
    
    # Tool Calling Framework
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    
    # Agent deliverables (key: agent name)
    agent_outputs: Annotated[Dict[str, Dict[str, Any]], operator.ior]
    
    # Validation & Citations
    citations: List[Dict[str, Any]]
    confidence_score: float
    groundedness_ratio: float
    is_eval_passed: bool
    evaluation_notes: str
    retry_count: int
    
    # Routing & Flow
    next_agent: str
    sender: str
    
    # Final consolidated output
    final_answer: str
    
    # Execution metrics
    execution_trace: Annotated[List[Dict[str, Any]], operator.add]
    errors: Annotated[List[str], operator.add]
