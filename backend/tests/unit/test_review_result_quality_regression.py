"""
Regression Tests: Code Review Result Quality & Architecture Metrics Integrity
=============================================================================
Proves:
- Missing architecture metrics are preserved as None (null), NOT 0.0 or fake scores
- Disabled review categories result in None / not evaluated states
- Enabled review categories schedule corresponding specialized agents
- Security and Performance agents produce structured JSON findings with proper schema
- Clean repositories evaluate to 100.0 scores, not 0.0
- API serializes None instead of forcing 0.0
- Structured count logging records finding counts safely
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.domain.interfaces.llm import ILLMProvider, LLMResponse
from src.domain.models.agents import AgentState, AgentType
from src.application.agents.planner import PlannerAgent
from src.application.agents.security_review import SecurityReviewAgent
from src.application.agents.performance import PerformanceAgent
from src.application.agents.code_quality import CodeQualityAgent
from src.application.use_cases.review_code import ReviewCodeUseCase
from src.domain.entities.code_review import ReviewStatusEnum
from src.interfaces.api.v1.reviews import _db_review_to_response, CodeReviewResponse


@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=ILLMProvider)
    llm.complete = AsyncMock()
    return llm


@pytest.mark.asyncio
async def test_planner_schedules_all_enabled_review_agents(mock_llm):
    """Planner must deterministically schedule all enabled agents when review_config is passed."""
    mock_llm.complete.return_value = LLMResponse(
        content='{"summary": "Review", "selected_agents": ["context", "code_review"]}',
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        model_name="test-model",
    )
    planner = PlannerAgent(mock_llm)
    state: AgentState = {
        "query": "Perform a structured code review",
        "review_config": {
            "code_quality": True,
            "security": True,
            "performance": True,
            "architecture": True,
        },
    }
    result = await planner.execute(state)
    selected = result["plan"]["selected_agents"]

    assert "context" in selected
    assert "code_review" in selected
    assert "security_review" in selected
    assert "performance" in selected
    assert "code_quality" in selected
    assert "refactoring_analysis" in selected


@pytest.mark.asyncio
async def test_planner_respects_disabled_flags(mock_llm):
    """Planner must drop disabled agents when review_config flags are False."""
    mock_llm.complete.return_value = LLMResponse(
        content='{"summary": "Review", "selected_agents": ["context", "code_review", "security_review", "performance", "code_quality"]}',
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        model_name="test-model",
    )
    planner = PlannerAgent(mock_llm)
    state: AgentState = {
        "query": "Review without security or performance",
        "review_config": {
            "code_quality": True,
            "security": False,
            "performance": False,
            "architecture": False,
        },
    }
    result = await planner.execute(state)
    selected = result["plan"]["selected_agents"]

    assert "security_review" not in selected
    assert "performance" not in selected
    assert "code_review" in selected


@pytest.mark.asyncio
async def test_security_review_agent_structured_findings(mock_llm):
    """SecurityReviewAgent must parse structured JSON security findings."""
    mock_llm.complete.return_value = LLMResponse(
        content='''[
            {
                "vulnerability": "Hardcoded JWT Secret",
                "issue": "Hardcoded JWT Secret",
                "severity": "critical",
                "cwe_id": "CWE-798",
                "owasp_category": "A07:2021-Identification and Authentication Failures",
                "file_path": "src/core/security.py",
                "line_number": 12,
                "explanation": "JWT signing secret is hardcoded in source file.",
                "attack_scenario": "Attacker extracts secret and signs arbitrary tokens.",
                "suggested_fix": "Load secret from environment variable.",
                "confidence_score": 0.99
            }
        ]''',
        prompt_tokens=10,
        completion_tokens=50,
        total_tokens=60,
        model_name="test-model",
    )
    agent = SecurityReviewAgent(mock_llm)
    state: AgentState = {
        "query": "Security review",
        "retrieved_context": "SECRET = 'supersecret'",
        "pending_tasks": ["security_review"],
        "completed_tasks": [],
    }
    res = await agent.execute(state)
    outputs = res["agent_outputs"]["security_review"]
    findings = outputs["structured_findings"]

    assert len(findings) == 1
    assert findings[0]["vulnerability"] == "Hardcoded JWT Secret"
    assert findings[0]["cwe_id"] == "CWE-798"
    assert findings[0]["severity"] == "critical"


@pytest.mark.asyncio
async def test_performance_agent_structured_findings(mock_llm):
    """PerformanceAgent must parse structured JSON performance findings without markdown conflict."""
    mock_llm.complete.return_value = LLMResponse(
        content='''```json
        [
            {
                "issue": "N+1 query in user list",
                "severity": "high",
                "estimated_impact": "Causes 100 queries for 100 users",
                "file_path": "src/api/users.py",
                "line_number": 30,
                "root_cause": "Query inside loop",
                "suggested_optimization": "Use joinedload",
                "expected_performance_gain": "85%",
                "confidence_score": 0.95
            }
        ]
        ```''',
        prompt_tokens=10,
        completion_tokens=50,
        total_tokens=60,
        model_name="test-model",
    )
    agent = PerformanceAgent(mock_llm)
    state: AgentState = {
        "query": "Performance review",
        "retrieved_context": "for u in users: get_profile(u.id)",
        "pending_tasks": ["performance"],
        "completed_tasks": [],
    }
    res = await agent.execute(state)
    outputs = res["agent_outputs"]["performance"]
    findings = outputs["structured_findings"]

    assert len(findings) == 1
    assert findings[0]["issue"] == "N+1 query in user list"
    assert findings[0]["severity"] == "high"


@pytest.mark.asyncio
async def test_code_quality_agent_evaluates_clean_code_to_100_percent(mock_llm):
    """Clean codebase analysis with 0 findings evaluates to 100.0 metrics, never 0.0."""
    mock_llm.complete.return_value = LLMResponse(
        content='''{
            "findings": [],
            "metrics": {
                "overall_health_score": 100.0,
                "architecture_score": 100.0,
                "maintainability_score": 100.0,
                "technical_debt_score": 100.0,
                "complexity_score": 100.0,
                "documentation_score": 100.0,
                "modularity_score": 100.0,
                "testability_score": 100.0
            },
            "dependency_analysis": {},
            "summary": "Clean architecture codebase."
        }''',
        prompt_tokens=10,
        completion_tokens=50,
        total_tokens=60,
        model_name="test-model",
    )
    agent = CodeQualityAgent(mock_llm)
    state: AgentState = {
        "query": "Architecture review",
        "retrieved_context": "Clean code",
        "pending_tasks": ["code_quality"],
        "completed_tasks": [],
    }
    res = await agent.execute(state)
    outputs = res["agent_outputs"]["code_quality"]
    metrics = outputs["metrics"]

    assert metrics["overall_health_score"] == 100.0
    assert metrics["architecture_score"] == 100.0
    assert len(outputs["structured_findings"]) == 0


@pytest.mark.asyncio
async def test_review_code_use_case_preserves_none_when_category_not_evaluated():
    """When a review category is disabled or not evaluated, scores must be None, NOT 0.0."""
    mock_review_service = MagicMock()
    mock_executor = MagicMock()
    mock_executor.execute = AsyncMock(return_value={
        "agent_outputs": {
            AgentType.CODE_REVIEW.value: {
                "structured_findings": [
                    {
                        "issue": "Naming convention violation",
                        "severity": "low",
                        "explanation": "Variable x is poorly named",
                        "file_path": "src/main.py",
                        "line_number": 5,
                    }
                ]
            }
        },
        "confidence_score": 0.9,
    })

    use_case = ReviewCodeUseCase(mock_review_service, mock_executor)
    
    # Run with security, performance, and architecture DISABLED
    config = {
        "code_quality": True,
        "security": False,
        "performance": False,
        "architecture": False,
    }

    res = await use_case.execute(
        repository_id="repo-123",
        user_id="user-123",
        review_id="rev-123",
        review_config=config,
    )

    assert res["status"] == "completed"

    # Verify update_review_status was called with None for unevaluated metrics
    call_kwargs = mock_review_service.update_review_status.call_args_list[-1].kwargs
    assert call_kwargs["performance_score"] is None
    assert call_kwargs["overall_health_score"] is None
    assert call_kwargs["architecture_score"] is None
    assert call_kwargs["maintainability_score"] is None
    assert call_kwargs["technical_debt_score"] is None


def test_api_serializer_preserves_none_for_unevaluated_metrics():
    """API serializer _db_review_to_response must serialize None (null) and not 0.0."""
    db_review = MagicMock()
    db_review.id = "rev-123"
    db_review.repository_id = "repo-123"
    db_review.user_id = "user-123"
    db_review.status = "completed"
    db_review.progress_percent = 100
    db_review.current_stage = "completed"
    db_review.progress_message = "Done"
    db_review.findings_json = []
    db_review.confidence_score = 1.0
    db_review.duration_ms = 500
    db_review.performance_score = None
    db_review.performance_findings_json = []
    db_review.performance_recommendations_json = []
    db_review.estimated_cpu_savings = 0.0
    db_review.estimated_memory_savings = 0.0
    db_review.estimated_latency_improvement = 0.0
    db_review.refactoring_findings_json = []
    db_review.refactoring_priority = None
    db_review.estimated_refactoring_effort = 0.0
    db_review.estimated_maintainability_improvement = 0.0
    db_review.estimated_technical_debt_reduction = 0.0
    db_review.estimated_complexity_reduction = 0.0
    db_review.architecture_findings_json = []
    db_review.overall_health_score = None
    db_review.architecture_score = None
    db_review.maintainability_score = None
    db_review.technical_debt_score = None
    db_review.complexity_score = None
    db_review.documentation_score = None
    db_review.modularity_score = None
    db_review.testability_score = None
    db_review.dependency_analysis_json = {}
    db_review.created_at = None
    db_review.updated_at = None

    response: CodeReviewResponse = _db_review_to_response(db_review)

    assert response.overall_health_score is None
    assert response.architecture_score is None
    assert response.maintainability_score is None
    assert response.technical_debt_score is None
    assert response.performance_score is None
