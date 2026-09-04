from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from src.interfaces.api.dependencies import (
    get_db_session as get_db,
    get_current_user,
    get_agent_use_case,
    get_repository_service,
    get_apply_fix_use_case,
    get_verify_applied_fix_use_case,
    get_verify_applied_fix_tests_use_case,
    get_commit_applied_fix_use_case,
    get_push_fix_branch_use_case,
    get_create_fix_pull_request_use_case,
    _get_llm_provider,
)
from src.domain.entities.user import User
from src.domain.entities.fix_suggestion import FixSuggestion
from src.domain.entities.verification import StaticVerificationResult
from src.domain.entities.sandbox import SandboxVerificationResult
from src.domain.entities.git import GitCommitResult, GitPushResult, GitPullRequestResult
from src.application.services.code_review_service import CodeReviewService
from src.application.services.repository_service import RepositoryService
from src.infrastructure.repositories.code_review_repository import CodeReviewRepository
from src.application.use_cases.review_code import ReviewCodeUseCase
from src.application.use_cases.agent_execution import ExecuteAgentWorkflowUseCase
from src.application.use_cases.apply_fix import ApplyFixSuggestionUseCase
from src.application.use_cases.verify_applied_fix import VerifyAppliedFixUseCase
from src.application.use_cases.verify_applied_fix_tests import VerifyAppliedFixTestsUseCase
from src.application.use_cases.commit_applied_fix import CommitAppliedFixUseCase
from src.application.use_cases.push_fix_branch import PushFixBranchUseCase
from src.application.use_cases.create_fix_pull_request import CreateFixPullRequestUseCase
from src.core.config import settings

# --- Dependency factories ---

def get_code_review_service(db: Session = Depends(get_db)) -> CodeReviewService:
    """Provide a CodeReviewService backed by the request-scoped DB session."""
    repo = CodeReviewRepository(db)
    return CodeReviewService(repo)


def _extract_user_id(current_user: Any) -> str:
    """Extract authenticated user ID from UserPayload or dict, raising 401 if missing."""
    if isinstance(current_user, dict):
        uid = current_user.get("sub") or current_user.get("id")
    else:
        uid = getattr(current_user, "id", None) or getattr(current_user, "sub", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid user token")
    return str(uid)


router = APIRouter(prefix="/reviews", tags=["reviews"])


from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Progress & response schemas
# ---------------------------------------------------------------------------

class CodeReviewProgressResponse(BaseModel):
    """Minimal progress-only response for polling clients."""
    id: str
    status: str
    progress_percent: int = 0
    current_stage: str = "queued"
    progress_message: Optional[str] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None


class CodeReviewResponse(BaseModel):
    """Full review response with progress fields and mapped findings."""
    id: str
    repository_id: str
    user_id: str
    status: str
    # Progress tracking fields
    progress_percent: int = 0
    current_stage: str = "queued"
    progress_message: Optional[str] = None
    # Result data
    findings: List[Dict] = Field(default_factory=list)
    confidence_score: float = 1.0
    duration_ms: Optional[int] = None
    # Performance
    performance_score: Optional[float] = None
    performance_findings: List[Dict] = Field(default_factory=list)
    performance_recommendations: List[Dict] = Field(default_factory=list)
    estimated_cpu_savings: float = 0.0
    estimated_memory_savings: float = 0.0
    estimated_latency_improvement: float = 0.0
    # Refactoring
    refactoring_findings: List[Dict] = Field(default_factory=list)
    refactoring_priority: Optional[str] = None
    estimated_refactoring_effort: float = 0.0
    estimated_maintainability_improvement: float = 0.0
    estimated_technical_debt_reduction: float = 0.0
    estimated_complexity_reduction: float = 0.0
    # Architecture
    architecture_findings: List[Dict] = Field(default_factory=list)
    overall_health_score: float = 0.0
    architecture_score: float = 0.0
    maintainability_score: float = 0.0
    technical_debt_score: float = 0.0
    complexity_score: float = 0.0
    documentation_score: float = 0.0
    modularity_score: float = 0.0
    testability_score: float = 0.0
    dependency_analysis: Dict = Field(default_factory=dict)
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


def _db_review_to_response(db_review: Any) -> CodeReviewResponse:
    """Convert a DBCodeReview ORM object to a CodeReviewResponse schema."""
    def _get_str(attr: str, default: str = "") -> str:
        val = getattr(db_review, attr, default)
        if val is None or not isinstance(val, str):
            return str(val) if val is not None and not hasattr(val, "_mock_name") else default
        return val

    def _get_int(attr: str, default: int = 0) -> int:
        val = getattr(db_review, attr, default)
        if val is None or isinstance(val, (int, float)):
            return int(val) if val is not None else default
        return default

    def _get_float(attr: str, default: float = 0.0) -> float:
        val = getattr(db_review, attr, default)
        if val is None or isinstance(val, (int, float)):
            return float(val) if val is not None else default
        return default

    def _get_list(attr: str) -> List[Dict]:
        val = getattr(db_review, attr, [])
        return val if isinstance(val, list) else []

    def _get_dict(attr: str) -> Dict:
        val = getattr(db_review, attr, {})
        return val if isinstance(val, dict) else {}

    return CodeReviewResponse(
        id=_get_str("id", "review_id"),
        repository_id=_get_str("repository_id", "repo_id"),
        user_id=_get_str("user_id", "user_id"),
        status=_get_str("status", "pending"),
        progress_percent=_get_int("progress_percent", 0),
        current_stage=_get_str("current_stage", "queued"),
        progress_message=getattr(db_review, "progress_message", None) if not hasattr(getattr(db_review, "progress_message", None), "_mock_name") else None,
        # Map findings_json -> findings
        findings=_get_list("findings_json"),
        confidence_score=_get_float("confidence_score", 1.0),
        duration_ms=getattr(db_review, "duration_ms", None) if isinstance(getattr(db_review, "duration_ms", None), int) else None,
        performance_score=getattr(db_review, "performance_score", None) if isinstance(getattr(db_review, "performance_score", None), (int, float)) else None,
        performance_findings=_get_list("performance_findings_json"),
        performance_recommendations=_get_list("performance_recommendations_json"),
        estimated_cpu_savings=_get_float("estimated_cpu_savings", 0.0),
        estimated_memory_savings=_get_float("estimated_memory_savings", 0.0),
        estimated_latency_improvement=_get_float("estimated_latency_improvement", 0.0),
        refactoring_findings=_get_list("refactoring_findings_json"),
        refactoring_priority=getattr(db_review, "refactoring_priority", None) if isinstance(getattr(db_review, "refactoring_priority", None), str) else None,
        estimated_refactoring_effort=_get_float("estimated_refactoring_effort", 0.0),
        estimated_maintainability_improvement=_get_float("estimated_maintainability_improvement", 0.0),
        estimated_technical_debt_reduction=_get_float("estimated_technical_debt_reduction", 0.0),
        estimated_complexity_reduction=_get_float("estimated_complexity_reduction", 0.0),
        architecture_findings=_get_list("architecture_findings_json"),
        overall_health_score=_get_float("overall_health_score", 0.0),
        architecture_score=_get_float("architecture_score", 0.0),
        maintainability_score=_get_float("maintainability_score", 0.0),
        technical_debt_score=_get_float("technical_debt_score", 0.0),
        complexity_score=_get_float("complexity_score", 0.0),
        documentation_score=_get_float("documentation_score", 0.0),
        modularity_score=_get_float("modularity_score", 0.0),
        testability_score=_get_float("testability_score", 0.0),
        dependency_analysis=_get_dict("dependency_analysis_json"),
        created_at=getattr(db_review, "created_at", None) if not hasattr(getattr(db_review, "created_at", None), "_mock_name") else None,
        updated_at=getattr(db_review, "updated_at", None) if not hasattr(getattr(db_review, "updated_at", None), "_mock_name") else None,
    )


class ReviewConfigSchema(BaseModel):
    strictness: str = Field("medium", description="Strictness level: low, medium, high")
    code_quality: bool = Field(True, alias="codeQuality")
    documentation: bool = True
    architecture: bool = False
    security: bool = True
    performance: bool = True

    model_config = {"populate_by_name": True}

    @field_validator("strictness")
    @classmethod
    def validate_strictness(cls, v: str) -> str:
        val = str(v).lower()
        mapping = {"lenient": "low", "balanced": "medium", "strict": "high"}
        val = mapping.get(val, val)
        if val not in ("low", "medium", "high"):
            raise ValueError("strictness must be one of: low, medium, high, lenient, balanced, strict")
        return val


class StartReviewRequest(BaseModel):
    repository_id: str
    files: Optional[List[str]] = None
    config: Optional[ReviewConfigSchema] = None


import asyncio

# In-memory registry of active asyncio tasks running reviews
ACTIVE_REVIEW_TASKS: Dict[str, asyncio.Task] = {}


@router.post("/start", status_code=202)
async def start_review(
    request: StartReviewRequest,
    background_tasks: BackgroundTasks,
    current_user: Any = Depends(get_current_user),
    service: CodeReviewService = Depends(get_code_review_service),
    repo_service: RepositoryService = Depends(get_repository_service),
    agent_executor: ExecuteAgentWorkflowUseCase = Depends(get_agent_use_case),
):
    """
    Start an AI code review for the given repository.

    Returns 202 Accepted immediately with a real review_id persisted in PostgreSQL.
    Enforces that the target repository belongs to the authenticated user.
    """
    user_id = _extract_user_id(current_user)

    # Enforce repository ownership before starting review
    repo = repo_service.get_repository(user_id, request.repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Wire the use case with the injected, fully-configured agent executor
    use_case = ReviewCodeUseCase(
        code_review_service=service,
        agent_executor=agent_executor,
    )

    import uuid
    review_id = str(uuid.uuid4())

    review_config = request.config or ReviewConfigSchema()

    from src.domain.entities.code_review import CodeReviewCreate
    service.create_review(CodeReviewCreate(repository_id=request.repository_id), user_id, review_id)

    async def _run():
        try:
            await use_case.execute(
                repository_id=request.repository_id,
                user_id=user_id,
                files_to_review=request.files,
                review_id=review_id,
                review_config=review_config,
            )
        except Exception:
            pass

    task = asyncio.create_task(_run())
    ACTIVE_REVIEW_TASKS[review_id] = task
    task.add_done_callback(lambda _: ACTIVE_REVIEW_TASKS.pop(review_id, None))

    return {
        "message": "Review started",
        "review_id": review_id,
        "status": "pending",
    }


@router.post("/{review_id}/cancel")
def cancel_review(
    review_id: str,
    current_user: Any = Depends(get_current_user),
    service: CodeReviewService = Depends(get_code_review_service),
):
    """
    Cancel an active AI code review.
    Enforces review ownership (returns 404 for unauthorized users).
    Is idempotent for terminal states (completed, failed, cancelled).
    """
    user_id = _extract_user_id(current_user)
    review = service.get_review(review_id, user_id=user_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    from src.domain.entities.code_review import ReviewStatusEnum

    if review.status == ReviewStatusEnum.COMPLETED.value:
        return {"message": "Review is already completed", "status": "completed", "review_id": review_id}

    if review.status == ReviewStatusEnum.FAILED.value:
        return {"message": "Review is already failed", "status": "failed", "review_id": review_id}

    if review.status == ReviewStatusEnum.CANCELLED.value:
        return {"message": "Review is already cancelled", "status": "cancelled", "review_id": review_id}

    # Cancel in-memory task if running
    task = ACTIVE_REVIEW_TASKS.pop(review_id, None)
    if task and not task.done():
        task.cancel()

    # Update DB status to CANCELLED
    service.update_review_status(
        review_id,
        ReviewStatusEnum.CANCELLED,
        progress_percent=min(review.progress_percent or 10, 99),
        current_stage="cancelled",
        progress_message="Review cancelled by user",
    )

    return {
        "message": "Review cancelled successfully",
        "status": "cancelled",
        "review_id": review_id,
    }


@router.delete("/{review_id}")
def delete_review_endpoint(
    review_id: str,
    current_user: Any = Depends(get_current_user),
    service: CodeReviewService = Depends(get_code_review_service),
):
    """Delete a review from history. Cancels background task if active."""
    user_id = _extract_user_id(current_user)
    task = ACTIVE_REVIEW_TASKS.pop(review_id, None)
    if task and not task.done():
        task.cancel()
    deleted = service.delete_review(review_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review deleted successfully"}



@router.get("", response_model=List[CodeReviewResponse])
def list_reviews(
    repository_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Any = Depends(get_current_user),
    service: CodeReviewService = Depends(get_code_review_service),
):
    """List all code reviews owned by the authenticated user."""
    user_id = _extract_user_id(current_user)
    db_reviews = service.list_user_reviews(
        user_id=user_id,
        repository_id=repository_id,
        status=status,
        skip=skip,
        limit=limit,
    )
    return [_db_review_to_response(r) for r in db_reviews]


@router.get("/history/{repository_id}")
def get_review_history(
    repository_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Any = Depends(get_current_user),
    service: CodeReviewService = Depends(get_code_review_service),
    repo_service: RepositoryService = Depends(get_repository_service),
):
    user_id = _extract_user_id(current_user)
    # Enforce repository ownership
    repo = repo_service.get_repository(user_id, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    reviews = service.get_repository_reviews(repository_id, user_id=user_id, skip=skip, limit=limit)
    return reviews


@router.get("/{review_id}/progress", response_model=CodeReviewProgressResponse)
def get_review_progress(
    review_id: str,
    current_user: Any = Depends(get_current_user),
    service: CodeReviewService = Depends(get_code_review_service),
):
    """Lightweight progress-only endpoint for efficient polling during active reviews."""
    user_id = _extract_user_id(current_user)
    review = service.get_review(review_id, user_id=user_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return CodeReviewProgressResponse(
        id=review.id,
        status=review.status,
        progress_percent=review.progress_percent or 0,
        current_stage=review.current_stage or "queued",
        progress_message=review.progress_message,
        duration_ms=review.duration_ms,
        error_message=review.progress_message if review.status == "failed" else None,
    )


@router.get("/{review_id}", response_model=CodeReviewResponse)
def get_review(
    review_id: str,
    current_user: Any = Depends(get_current_user),
    service: CodeReviewService = Depends(get_code_review_service)
):
    """Retrieve a full review result including findings, scores, and progress metadata."""
    user_id = _extract_user_id(current_user)
    review = service.get_review(review_id, user_id=user_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return _db_review_to_response(review)


@router.get("/{review_id}/performance")
def get_performance(
    review_id: str,
    current_user: Any = Depends(get_current_user),
    service: CodeReviewService = Depends(get_code_review_service)
):
    user_id = _extract_user_id(current_user)
    review = service.get_review(review_id, user_id=user_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return {
        "performance_score": getattr(review, "performance_score", None),
        "performance_findings": getattr(review, "performance_findings_json", []),
        "performance_recommendations": getattr(review, "performance_recommendations_json", []),
        "estimated_cpu_savings": getattr(review, "estimated_cpu_savings", 0.0),
        "estimated_memory_savings": getattr(review, "estimated_memory_savings", 0.0),
        "estimated_latency_improvement": getattr(review, "estimated_latency_improvement", 0.0),
    }


@router.get("/{review_id}/refactoring")
def get_refactoring(
    review_id: str,
    current_user: Any = Depends(get_current_user),
    service: CodeReviewService = Depends(get_code_review_service)
):
    """Return refactoring analysis results for a completed review."""
    user_id = _extract_user_id(current_user)
    review = service.get_review(review_id, user_id=user_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return {
        "refactoring_findings": getattr(review, "refactoring_findings_json", []),
        "refactoring_priority": getattr(review, "refactoring_priority", None),
        "estimated_refactoring_effort": getattr(review, "estimated_refactoring_effort", 0.0),
        "estimated_maintainability_improvement": getattr(review, "estimated_maintainability_improvement", 0.0),
        "estimated_technical_debt_reduction": getattr(review, "estimated_technical_debt_reduction", 0.0),
        "estimated_complexity_reduction": getattr(review, "estimated_complexity_reduction", 0.0),
    }


@router.get("/{review_id}/architecture")
def get_architecture(
    review_id: str,
    current_user: Any = Depends(get_current_user),
    service: CodeReviewService = Depends(get_code_review_service)
):
    """Return architecture & code quality analysis results for a completed review."""
    user_id = _extract_user_id(current_user)
    review = service.get_review(review_id, user_id=user_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return {
        "architecture_findings": getattr(review, "architecture_findings_json", []),
        "overall_health_score": getattr(review, "overall_health_score", 0.0),
        "architecture_score": getattr(review, "architecture_score", 0.0),
        "maintainability_score": getattr(review, "maintainability_score", 0.0),
        "technical_debt_score": getattr(review, "technical_debt_score", 0.0),
        "complexity_score": getattr(review, "complexity_score", 0.0),
        "documentation_score": getattr(review, "documentation_score", 0.0),
        "modularity_score": getattr(review, "modularity_score", 0.0),
        "testability_score": getattr(review, "testability_score", 0.0),
        "dependency_analysis": getattr(review, "dependency_analysis_json", {}),
    }


# ---------------------------------------------------------------------------
# Phase 11.2B-3 — Fix Suggestion API endpoints
# ---------------------------------------------------------------------------

def get_fix_suggestion_agent():
    """Dependency factory: builds a FixSuggestionAgent using the shared LLM provider."""
    from src.application.agents.fix_suggestion import FixSuggestionAgent
    return FixSuggestionAgent(llm_provider=_get_llm_provider())


def _safe_finding_index(finding_index: int) -> int:
    """Reject negative finding indexes before they reach the service layer."""
    if finding_index < 0:
        raise HTTPException(
            status_code=422,
            detail=f"finding_index must be >= 0, got {finding_index}",
        )
    return finding_index


@router.post("/{review_id}/findings/{finding_index}/fix", status_code=200)
async def generate_fix(
    review_id: str,
    finding_index: int,
    current_user: Any = Depends(get_current_user),
    service: CodeReviewService = Depends(get_code_review_service),
    fix_agent=Depends(get_fix_suggestion_agent),
):
    """
    Generate an automated fix suggestion for a single finding in a completed review.

    Enforces:
    - Review ownership (404 for unauthorized users)
    - Review status == COMPLETED
    - Valid, non-negative finding_index
    - Idempotency: returns existing suggestion without calling LLM again
    - Read-only: no repository files are modified
    """
    user_id = _extract_user_id(current_user)
    _safe_finding_index(finding_index)

    # Ownership-enforced load (None → 404, preventing resource-existence leakage)
    review = service.get_review(review_id, user_id=user_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Validate review status before hitting agent
    from src.domain.entities.code_review import ReviewStatusEnum
    if review.status != ReviewStatusEnum.COMPLETED.value:
        raise HTTPException(
            status_code=409,
            detail=f"Fix generation requires a completed review (current status: '{review.status}')",
        )

    findings = list(review.findings_json or [])
    if finding_index >= len(findings):
        raise HTTPException(
            status_code=422,
            detail=f"finding_index {finding_index} out of range (review has {len(findings)} findings)",
        )

    # Idempotency check — return immediately without LLM call
    existing_fix = findings[finding_index].get("fix_suggestion")
    if existing_fix:
        return {"fix_suggestion": existing_fix, "cached": True}

    # Build domain ReviewFinding for the agent
    from src.domain.entities.code_review import ReviewFinding, SeverityEnum
    finding_dict = findings[finding_index]
    try:
        severity_val = finding_dict.get("severity", "medium")
        try:
            severity = SeverityEnum(severity_val)
        except ValueError:
            severity = SeverityEnum.MEDIUM

        finding = ReviewFinding(
            issue=finding_dict.get("issue", "Unknown issue"),
            severity=severity,
            explanation=finding_dict.get("explanation", ""),
            suggested_fix=finding_dict.get("suggested_fix"),
            confidence_score=float(finding_dict.get("confidence_score", 1.0)),
            file_path=finding_dict.get("file_path"),
            line_number=finding_dict.get("line_number"),
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Malformed finding data: {exc}")

    # Derive repository_id from review — never trust client-supplied value
    repository_id = review.repository_id

    # Invoke agent (read-only, in-memory)
    from src.core.errors import LLMQuotaExceededError, WorkflowExecutionError
    try:
        fix_suggestion = await fix_agent.generate_fix(
            finding=finding,
            finding_index=finding_index,
            repository_id=repository_id,
        )
    except LLMQuotaExceededError as exc:
        raise HTTPException(status_code=429, detail=f"LLM quota exceeded: {exc}")
    except WorkflowExecutionError as exc:
        raise HTTPException(status_code=502, detail=f"Fix generation failed: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Unexpected fix agent error: {exc}")

    # Persist — service handles atomicity and idempotency
    try:
        persisted_fix = service.update_finding_fix_suggestion(
            review_id=review_id,
            finding_index=finding_index,
            fix_suggestion=fix_suggestion,
            user_id=user_id,
        )
    except (ValueError, IndexError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {"fix_suggestion": persisted_fix, "cached": False}


@router.post("/{review_id}/findings/{finding_index}/fix/accept", status_code=200)
def accept_fix(
    review_id: str,
    finding_index: int,
    current_user: Any = Depends(get_current_user),
    service: CodeReviewService = Depends(get_code_review_service),
):
    """
    Accept a generated fix suggestion (metadata-only, no file modification).

    Decision policy:
    - pending  → accepted
    - rejected → accepted  (explicit override allowed)
    - accepted → accepted  (idempotent)
    """
    user_id = _extract_user_id(current_user)
    _safe_finding_index(finding_index)

    review = service.get_review(review_id, user_id=user_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    from src.domain.entities.fix_suggestion import FixUserDecision
    try:
        updated_fix = service.update_finding_decision(
            review_id=review_id,
            finding_index=finding_index,
            decision=FixUserDecision.ACCEPTED,
            user_id=user_id,
        )
    except IndexError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except KeyError:
        raise HTTPException(status_code=404, detail="No fix suggestion exists for this finding")

    return {"fix_suggestion": updated_fix}


@router.post("/{review_id}/findings/{finding_index}/fix/reject", status_code=200)
def reject_fix(
    review_id: str,
    finding_index: int,
    current_user: Any = Depends(get_current_user),
    service: CodeReviewService = Depends(get_code_review_service),
):
    """
    Reject a generated fix suggestion (metadata-only, no file modification).

    Decision policy:
    - pending  → rejected
    - accepted → rejected  (explicit override allowed)
    - rejected → rejected  (idempotent)
    """
    user_id = _extract_user_id(current_user)
    _safe_finding_index(finding_index)

    review = service.get_review(review_id, user_id=user_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    from src.domain.entities.fix_suggestion import FixUserDecision
    try:
        updated_fix = service.update_finding_decision(
            review_id=review_id,
            finding_index=finding_index,
            decision=FixUserDecision.REJECTED,
            user_id=user_id,
        )
    except IndexError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except KeyError:
        raise HTTPException(status_code=404, detail="No fix suggestion exists for this finding")

    return {"fix_suggestion": updated_fix}


@router.post("/{review_id}/findings/{finding_index}/fix/apply", status_code=200)
async def apply_fix(
    review_id: str,
    finding_index: int,
    current_user: Any = Depends(get_current_user),
    use_case: ApplyFixSuggestionUseCase = Depends(get_apply_fix_use_case),
):
    """
    Apply an accepted fix suggestion to the repository workspace file.

    Enforces:
    - User authentication and ownership of review and repository
    - Completed review status
    - Accepted user decision
    - Valid syntax verification status
    - Single-process concurrency lock per finding
    - Idempotency: re-applying returns existing applied state without duplicate mutation
    - Stale source conflict detection and compensating rollback on persistence failure
    - Zero LLM calls and zero arbitrary shell/git execution
    """
    user_id = _extract_user_id(current_user)
    _safe_finding_index(finding_index)

    from src.core.errors import ResourceNotFoundError, WorkflowExecutionError

    try:
        result = await use_case.execute(
            review_id=review_id,
            finding_index=finding_index,
            user_id=user_id,
        )
        return result
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except WorkflowExecutionError as exc:
        err_msg = str(exc)
        if "out of range" in err_msg or "finding_index must be" in err_msg or "invalid syntax" in err_msg:
            raise HTTPException(status_code=422, detail=err_msg)
        elif "Stale source" in err_msg or "completed review" in err_msg or "must be accepted" in err_msg:
            raise HTTPException(status_code=409, detail=err_msg)
        elif "Sandbox violation" in err_msg:
            raise HTTPException(status_code=400, detail=err_msg)
        elif "No fix suggestion exists" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        else:
            raise HTTPException(status_code=422, detail=err_msg)


class VerifyFixResponse(BaseModel):
    """Response schema for Tier-1 static verification of an applied fix."""
    verification: StaticVerificationResult
    fix_suggestion: FixSuggestion


@router.post(
    "/{review_id}/findings/{finding_index}/fix/verify",
    status_code=200,
    response_model=VerifyFixResponse,
)
async def verify_fix(
    review_id: str,
    finding_index: int,
    current_user: Any = Depends(get_current_user),
    use_case: VerifyAppliedFixUseCase = Depends(get_verify_applied_fix_use_case),
):
    """
    Verify an applied fix suggestion using in-memory Tier-1 static checks.

    Enforces:
    - User authentication and ownership of review and repository
    - Completed review status
    - Fix suggestion exists and application_status == applied
    - Read-only sandbox file access
    - Source hash integrity check (detects post-apply modification)
    - Re-verification safe and refresh-safe persistence
    - Zero LLM calls and zero subprocess/shell execution
    """
    user_id = _extract_user_id(current_user)
    _safe_finding_index(finding_index)

    from src.core.errors import ResourceNotFoundError, WorkflowExecutionError

    try:
        result = await use_case.execute(
            review_id=review_id,
            finding_index=finding_index,
            user_id=user_id,
        )
        return result
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except WorkflowExecutionError as exc:
        err_msg = str(exc)
        if "out of range" in err_msg or "finding_index must be" in err_msg:
            raise HTTPException(status_code=422, detail=err_msg)
        elif "must be applied" in err_msg or "completed review" in err_msg or "Cannot verify" in err_msg:
            raise HTTPException(status_code=409, detail=err_msg)
        elif "Sandbox violation" in err_msg or "Target path validation" in err_msg:
            raise HTTPException(status_code=400, detail=err_msg)
        elif "No fix suggestion exists" in err_msg or "Target file does not exist" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        else:
            raise HTTPException(status_code=422, detail=err_msg)


class VerifyFixTestsResponse(BaseModel):
    """Response schema for Tier-2 isolated container test verification of an applied fix."""
    verification: SandboxVerificationResult
    fix_suggestion: FixSuggestion


@router.post(
    "/{review_id}/findings/{finding_index}/fix/verify-tests",
    status_code=200,
    response_model=VerifyFixTestsResponse,
)
async def verify_fix_tests(
    review_id: str,
    finding_index: int,
    current_user: Any = Depends(get_current_user),
    use_case: VerifyAppliedFixTestsUseCase = Depends(get_verify_applied_fix_tests_use_case),
):
    """
    Execute Tier-2 isolated container test verification of an applied fix suggestion.

    Enforces:
    - User authentication and ownership of both review and repository
    - Completed review status
    - Fix suggestion exists and application_status == applied
    - Tier-1 static verification must be in PASSED state (prerequisite)
    - Source hash integrity check (detects post-apply modification)
    - Python/pytest only — all other frameworks return UNSUPPORTED without execution
    - Repository tests run in an ephemeral, network-disabled, resource-limited container
    - Zero LLM calls, zero host/subprocess execution, zero arbitrary command from client
    - Sandbox unavailable returns SANDBOX_UNAVAILABLE without host fallback
    - Ephemeral workspace cleaned up regardless of outcome
    """
    user_id = _extract_user_id(current_user)
    _safe_finding_index(finding_index)

    from src.core.errors import ResourceNotFoundError, WorkflowExecutionError

    try:
        result = await use_case.execute(
            review_id=review_id,
            finding_index=finding_index,
            user_id=user_id,
        )
        return result
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except WorkflowExecutionError as exc:
        err_msg = str(exc)
        if "out of range" in err_msg or "finding_index must be" in err_msg:
            raise HTTPException(status_code=422, detail=err_msg)
        elif ("must be applied" in err_msg or "completed review" in err_msg
              or "Cannot run" in err_msg or "Source file was modified" in err_msg
              or "static verification must" in err_msg):
            raise HTTPException(status_code=409, detail=err_msg)
        elif "Target path validation" in err_msg:
            raise HTTPException(status_code=400, detail=err_msg)
        elif "No fix suggestion exists" in err_msg or "Target file does not exist" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        else:
            raise HTTPException(status_code=422, detail=err_msg)

class CommitFixResponse(BaseModel):
    """Response schema for the local Git commit of an applied+verified fix suggestion."""
    git_commit: GitCommitResult
    fix_suggestion: FixSuggestion


@router.post(
    "/{review_id}/findings/{finding_index}/fix/git/commit",
    status_code=200,
    response_model=CommitFixResponse,
)
async def commit_fix(
    review_id: str,
    finding_index: int,
    current_user: Any = Depends(get_current_user),
    use_case: CommitAppliedFixUseCase = Depends(get_commit_applied_fix_use_case),
):
    """
    Create an isolated local Git commit for an applied and verified fix suggestion.

    This endpoint creates a commit on a dedicated AI fix branch
    (``ai-fix/rev-<id>-f<n>``) using temporary Git index isolation so that:
    - The user's active branch and HEAD are never changed.
    - User-staged changes in the primary Git index are never captured.
    - Only the single intended fix file is committed.
    - The commit is idempotent: repeated calls return the existing commit.

    Enforces:
    - User authentication and ownership of review and repository
    - Completed review status
    - Fix suggestion exists and application_status == applied
    - Tier-1 static verification must be in PASSED state (prerequisite)
    - Source hash integrity check (detects post-apply modification)
    - Per-repository asyncio mutex for concurrency safety
    - Zero push, zero GitHub write, zero LLM calls, zero shell execution
    - No arbitrary Git parameters accepted from the client
    """
    user_id = _extract_user_id(current_user)
    _safe_finding_index(finding_index)

    from src.core.errors import ResourceNotFoundError, WorkflowExecutionError

    try:
        result = await use_case.execute(
            review_id=review_id,
            finding_index=finding_index,
            user_id=user_id,
        )
        return CommitFixResponse(
            git_commit=result["git_commit"],
            fix_suggestion=FixSuggestion(**result["fix_suggestion"]) if isinstance(result["fix_suggestion"], dict) else result["fix_suggestion"],
        )
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except WorkflowExecutionError as exc:
        err_msg = str(exc)
        if "out of range" in err_msg or "finding_index must be" in err_msg:
            raise HTTPException(status_code=422, detail=err_msg)
        elif (
            "must be applied" in err_msg
            or "completed review" in err_msg
            or "static verification must" in err_msg
            or "Source file was modified" in err_msg
            or "Cannot commit a rejected" in err_msg
        ):
            raise HTTPException(status_code=409, detail=err_msg)
        elif "Target path validation" in err_msg or "Path validation failed" in err_msg:
            raise HTTPException(status_code=400, detail=err_msg)
        elif "No fix suggestion exists" in err_msg or "Target file does not exist" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        else:
            raise HTTPException(status_code=422, detail=err_msg)


class PushFixResponse(BaseModel):
    """Response schema for the remote Git push of a dedicated AI fix branch."""
    git_push: GitPushResult
    fix_suggestion: FixSuggestion


@router.post(
    "/{review_id}/findings/{finding_index}/fix/git/push",
    status_code=200,
    response_model=PushFixResponse,
)
async def push_fix_branch(
    review_id: str,
    finding_index: int,
    current_user: Any = Depends(get_current_user),
    use_case: PushFixBranchUseCase = Depends(get_push_fix_branch_use_case),
):
    """
    Push an already-created dedicated AI fix branch to the repository's trusted remote.

    Enforces:
    - User authentication and ownership of review and repository
    - Completed review status
    - Local Git commit prerequisite (verified branch name and commit SHA)
    - Trusted remote validation against server-side repository metadata
    - Exact ref push with structured argv (zero shell, zero force flags)
    - Active branch/HEAD/index/working tree remain untouched
    - Idempotent: repeated calls return existing pushed state
    - Zero PR creation, zero LLM calls, zero arbitrary client Git inputs
    """
    user_id = _extract_user_id(current_user)
    _safe_finding_index(finding_index)

    from src.core.errors import ResourceNotFoundError, WorkflowExecutionError

    try:
        result = await use_case.execute(
            review_id=review_id,
            finding_index=finding_index,
            user_id=user_id,
        )
        return PushFixResponse(
            git_push=result["git_push"],
            fix_suggestion=FixSuggestion(**result["fix_suggestion"]) if isinstance(result["fix_suggestion"], dict) else result["fix_suggestion"],
        )
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except WorkflowExecutionError as exc:
        err_msg = str(exc)
        if "out of range" in err_msg or "finding_index must be" in err_msg:
            raise HTTPException(status_code=422, detail=err_msg)
        elif (
            "must be applied" in err_msg
            or "completed review" in err_msg
            or "must have a local Git commit" in err_msg
            or "must be in 'committed' status" in err_msg
            or "Cannot push a rejected" in err_msg
        ):
            raise HTTPException(status_code=409, detail=err_msg)
        elif "Target path validation" in err_msg or "Path validation failed" in err_msg:
            raise HTTPException(status_code=400, detail=err_msg)
        elif "No fix suggestion exists" in err_msg or "Target file does not exist" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        else:
            raise HTTPException(status_code=422, detail=err_msg)


class CreatePullRequestResponse(BaseModel):
    """Response schema for the GitHub Pull Request creation from a pushed AI fix branch."""
    git_pull_request: GitPullRequestResult
    fix_suggestion: FixSuggestion


@router.post(
    "/{review_id}/findings/{finding_index}/fix/git/pull-request",
    status_code=200,
    response_model=CreatePullRequestResponse,
)
async def create_fix_pull_request(
    review_id: str,
    finding_index: int,
    current_user: Any = Depends(get_current_user),
    use_case: CreateFixPullRequestUseCase = Depends(get_create_fix_pull_request_use_case),
):
    """
    Create a GitHub Pull Request from an already-pushed dedicated AI fix branch.

    Enforces:
    - User authentication and ownership of review and repository
    - Completed review status
    - Local Git commit and Git push prerequisites
    - Head branch derived from persisted push state
    - Base branch derived from server-side repository configuration
    - Zero client-supplied operational GitHub parameters (no repo, base, head, title, body, token)
    - Zero auto-merge, zero PR approval, zero branch deletion, zero force push
    - Idempotent: returns existing PR if already created or open on GitHub
    - Zero LLM calls during PR creation
    """
    user_id = _extract_user_id(current_user)
    _safe_finding_index(finding_index)

    from src.core.errors import ResourceNotFoundError, WorkflowExecutionError

    try:
        result = await use_case.execute(
            review_id=review_id,
            finding_index=finding_index,
            user_id=user_id,
        )
        return CreatePullRequestResponse(
            git_pull_request=result["git_pull_request"],
            fix_suggestion=FixSuggestion(**result["fix_suggestion"]) if isinstance(result["fix_suggestion"], dict) else result["fix_suggestion"],
        )
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except WorkflowExecutionError as exc:
        err_msg = str(exc)
        if "out of range" in err_msg or "finding_index must be" in err_msg:
            raise HTTPException(status_code=422, detail=err_msg)
        elif (
            "must be applied" in err_msg
            or "completed review" in err_msg
            or "must have a local Git commit" in err_msg
            or "must be pushed" in err_msg
            or "must be in 'committed' status" in err_msg
            or "Cannot create a Pull Request for a rejected" in err_msg
        ):
            raise HTTPException(status_code=409, detail=err_msg)
        elif "Target path validation" in err_msg or "Path validation failed" in err_msg:
            raise HTTPException(status_code=400, detail=err_msg)
        elif "No fix suggestion exists" in err_msg or "Target file does not exist" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        else:
            raise HTTPException(status_code=422, detail=err_msg)


