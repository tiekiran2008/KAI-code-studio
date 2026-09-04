"""
test_non_quota_workflow_failure.py
===================================
Verifies that non-429 workflow exceptions in ExecuteAgentWorkflowUseCase and ReviewCodeUseCase
result in a FAILED review status with duration recorded, and NEVER result in a spurious
COMPLETED status with static fallback scores.

Phase 11.1B-1 corrections
--------------------------
- agent_execution.py wraps all non-quota exceptions in WorkflowExecutionError so that
  callers receive a typed exception and can distinguish it from LLMQuotaExceededError.
- review_code.py has an explicit WorkflowExecutionError handler (marks FAILED, persists
  duration_ms, re-raises) in addition to the generic Exception fallback.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, call

from src.core.errors import LLMQuotaExceededError, WorkflowExecutionError
from src.domain.entities.code_review import ReviewStatusEnum
from src.application.use_cases.review_code import ReviewCodeUseCase
from src.application.use_cases.agent_execution import ExecuteAgentWorkflowUseCase


def _make_service(review_id: str):
    service = MagicMock()
    fake_review = MagicMock()
    fake_review.status = ReviewStatusEnum.IN_PROGRESS.value
    service.get_review.return_value = fake_review
    service.create_review.return_value = fake_review
    service.update_review_status.return_value = fake_review
    return service


# ---------------------------------------------------------------------------
# ExecuteAgentWorkflowUseCase -- exception wrapping / re-raising
# ---------------------------------------------------------------------------

class TestExecuteAgentWorkflowUseCaseExceptionHandling:
    """Verify ExecuteAgentWorkflowUseCase exception re-raising behavior.

    The contract: non-quota exceptions are wrapped in WorkflowExecutionError
    so that callers receive a typed exception that is distinct from quota errors.
    """

    @pytest.mark.asyncio
    async def test_non_quota_exception_wrapped_and_re_raised(self):
        """RuntimeError from graph must be re-raised as WorkflowExecutionError."""
        llm = MagicMock()
        query_proc = MagicMock()
        use_case = ExecuteAgentWorkflowUseCase(llm_provider=llm, query_processor=query_proc)

        use_case.graph = MagicMock()
        use_case.graph.ainvoke = AsyncMock(side_effect=RuntimeError("Generic LLM Connection Timeout"))

        # agent_execution wraps non-quota exceptions in WorkflowExecutionError
        with pytest.raises(WorkflowExecutionError) as exc_info:
            await use_case.execute(query="Review code", repo_id="repo-1")

        assert "Generic LLM Connection Timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_non_quota_exception_is_not_swallowed(self):
        """Non-quota failure must never silently return empty outputs."""
        llm = MagicMock()
        query_proc = MagicMock()
        use_case = ExecuteAgentWorkflowUseCase(llm_provider=llm, query_processor=query_proc)

        use_case.graph = MagicMock()
        use_case.graph.ainvoke = AsyncMock(side_effect=ValueError("graph compilation error"))

        with pytest.raises(WorkflowExecutionError):
            await use_case.execute(query="Review code", repo_id="repo-2")

    @pytest.mark.asyncio
    async def test_quota_exception_re_raised_as_quota_error(self):
        """Generic Exception containing '429' must be re-raised as LLMQuotaExceededError."""
        llm = MagicMock()
        query_proc = MagicMock()
        use_case = ExecuteAgentWorkflowUseCase(llm_provider=llm, query_processor=query_proc)

        use_case.graph = MagicMock()
        use_case.graph.ainvoke = AsyncMock(side_effect=Exception("429 RESOURCE_EXHAUSTED"))

        with pytest.raises(LLMQuotaExceededError):
            await use_case.execute(query="Review code", repo_id="repo-1")

    @pytest.mark.asyncio
    async def test_typed_quota_error_re_raised_unchanged(self):
        """LLMQuotaExceededError from the graph must be re-raised as-is."""
        llm = MagicMock()
        query_proc = MagicMock()
        use_case = ExecuteAgentWorkflowUseCase(llm_provider=llm, query_processor=query_proc)

        use_case.graph = MagicMock()
        use_case.graph.ainvoke = AsyncMock(
            side_effect=LLMQuotaExceededError("quota hit in subgraph")
        )

        with pytest.raises(LLMQuotaExceededError) as exc_info:
            await use_case.execute(query="Review code", repo_id="repo-1")

        assert "quota hit in subgraph" in str(exc_info.value)


# ---------------------------------------------------------------------------
# ReviewCodeUseCase -- non-quota failure behavior
# ---------------------------------------------------------------------------

class TestReviewCodeUseCaseNonQuotaFailure:
    """Verify ReviewCodeUseCase non-429 failure behavior."""

    @pytest.mark.asyncio
    async def test_workflow_execution_error_marks_review_failed(self):
        """WorkflowExecutionError from agent_executor must mark review FAILED."""
        review_id = "test-review-workflow-err-001"
        service = _make_service(review_id)

        agent_executor = MagicMock()
        agent_executor.execute = AsyncMock(
            side_effect=WorkflowExecutionError("graph node crash")
        )

        use_case = ReviewCodeUseCase(
            code_review_service=service,
            agent_executor=agent_executor,
        )

        with pytest.raises(WorkflowExecutionError):
            await use_case.execute(
                repository_id="repo-100",
                user_id="user-100",
                review_id=review_id,
            )

        calls = service.update_review_status.call_args_list
        statuses_used = [c.args[1] for c in calls if c.args]
        assert ReviewStatusEnum.FAILED in statuses_used, (
            f"Expected FAILED in status updates, got: {statuses_used}"
        )
        assert ReviewStatusEnum.COMPLETED not in statuses_used, (
            "COMPLETED must never be set on WorkflowExecutionError"
        )

    @pytest.mark.asyncio
    async def test_workflow_execution_error_persists_duration_ms(self):
        """duration_ms must be persisted on WorkflowExecutionError."""
        review_id = "test-review-workflow-duration-002"
        service = _make_service(review_id)

        agent_executor = MagicMock()
        agent_executor.execute = AsyncMock(
            side_effect=WorkflowExecutionError("timeout in code-review agent node")
        )

        use_case = ReviewCodeUseCase(
            code_review_service=service,
            agent_executor=agent_executor,
        )

        with pytest.raises(WorkflowExecutionError):
            await use_case.execute(
                repository_id="repo-101",
                user_id="user-101",
                review_id=review_id,
            )

        # Find the FAILED update call and confirm duration_ms was passed
        failed_calls = [
            c for c in service.update_review_status.call_args_list
            if c.args and c.args[1] == ReviewStatusEnum.FAILED
        ]
        assert failed_calls, "Expected at least one FAILED status update"
        failed_kwargs = failed_calls[-1].kwargs
        assert "duration_ms" in failed_kwargs, "duration_ms must be persisted on failure"
        assert isinstance(failed_kwargs["duration_ms"], int)

    @pytest.mark.asyncio
    async def test_non_quota_exception_marks_review_failed(self):
        """Generic RuntimeError from agent_executor must mark review FAILED."""
        review_id = "test-review-non-quota-001"
        service = _make_service(review_id)

        agent_executor = MagicMock()
        agent_executor.execute = AsyncMock(side_effect=RuntimeError("Internal Agent Error"))

        use_case = ReviewCodeUseCase(
            code_review_service=service,
            agent_executor=agent_executor,
        )

        with pytest.raises(RuntimeError):
            await use_case.execute(
                repository_id="repo-100",
                user_id="user-100",
                review_id=review_id,
            )

        calls = service.update_review_status.call_args_list
        statuses_used = [c.args[1] for c in calls if c.args]
        assert ReviewStatusEnum.FAILED in statuses_used
        assert ReviewStatusEnum.COMPLETED not in statuses_used

    @pytest.mark.asyncio
    async def test_result_containing_error_dict_marks_failed(self):
        """If agent returns a result with an 'error' key, review must be FAILED."""
        review_id = "test-review-error-dict-002"
        service = _make_service(review_id)

        agent_executor = MagicMock()
        agent_executor.execute = AsyncMock(return_value={
            "error": "LLM output parsing crashed",
            "agent_outputs": {},
        })

        use_case = ReviewCodeUseCase(
            code_review_service=service,
            agent_executor=agent_executor,
        )

        with pytest.raises(RuntimeError) as exc_info:
            await use_case.execute(
                repository_id="repo-200",
                user_id="user-200",
                review_id=review_id,
            )

        assert "LLM output parsing crashed" in str(exc_info.value)
        calls = service.update_review_status.call_args_list
        statuses_used = [c.args[1] for c in calls if c.args]
        assert ReviewStatusEnum.FAILED in statuses_used
        assert ReviewStatusEnum.COMPLETED not in statuses_used

    @pytest.mark.asyncio
    async def test_successful_zero_finding_review_marks_completed(self):
        """A genuine successful workflow with zero findings must still mark COMPLETED."""
        review_id = "test-review-success-zero-003"
        service = _make_service(review_id)

        agent_executor = MagicMock()
        agent_executor.execute = AsyncMock(return_value={
            "agent_outputs": {
                "code_review": {"structured_findings": []},
                "performance": {"structured_findings": []},
            },
            "confidence_score": 1.0,
        })

        use_case = ReviewCodeUseCase(
            code_review_service=service,
            agent_executor=agent_executor,
        )

        res = await use_case.execute(
            repository_id="repo-300",
            user_id="user-300",
            review_id=review_id,
        )

        assert res["status"] == "completed"
        calls = service.update_review_status.call_args_list
        statuses_used = [c.args[1] for c in calls if c.args]
        assert ReviewStatusEnum.COMPLETED in statuses_used
        assert ReviewStatusEnum.FAILED not in statuses_used

