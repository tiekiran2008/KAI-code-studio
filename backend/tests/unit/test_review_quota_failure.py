"""
test_review_quota_failure.py
============================
Verifies that a Gemini 429 RESOURCE_EXHAUSTED error propagates correctly
through the pipeline and results in a FAILED review status — not a spurious
COMPLETED review with empty findings and heuristic scores.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.errors import LLMQuotaExceededError
from src.domain.entities.code_review import ReviewStatusEnum
from src.application.use_cases.review_code import ReviewCodeUseCase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(review_id: str):
    """Return a mock CodeReviewService with the minimum interface."""
    service = MagicMock()
    fake_review = MagicMock()
    fake_review.status = ReviewStatusEnum.IN_PROGRESS.value
    service.get_review.return_value = fake_review
    service.create_review.return_value = fake_review
    service.update_review_status.return_value = fake_review
    return service


# ---------------------------------------------------------------------------
# Tests for LLMQuotaExceededError propagation
# ---------------------------------------------------------------------------

class TestLLMQuotaExceededError:
    """Unit tests for the LLMQuotaExceededError domain exception."""

    def test_is_plain_exception(self):
        exc = LLMQuotaExceededError("429 RESOURCE_EXHAUSTED")
        assert isinstance(exc, Exception)
        assert "429" in str(exc)

    def test_default_message(self):
        exc = LLMQuotaExceededError()
        assert "quota" in str(exc).lower() or "429" in str(exc)

    def test_custom_message_preserved(self):
        msg = "quota exceeded for model gemini-3.6-flash"
        exc = LLMQuotaExceededError(msg)
        assert str(exc) == msg


# ---------------------------------------------------------------------------
# Tests for ReviewCodeUseCase quota-failure path
# ---------------------------------------------------------------------------

class TestReviewCodeUseCaseQuotaFailure:
    """
    Verify that when the agent_executor raises LLMQuotaExceededError,
    ReviewCodeUseCase marks the review as FAILED and does NOT call
    update_review_status with COMPLETED or any heuristic scores.
    """

    @pytest.mark.asyncio
    async def test_quota_error_marks_review_failed(self):
        review_id = "test-review-uuid-001"
        service = _make_service(review_id)

        agent_executor = MagicMock()
        agent_executor.execute = AsyncMock(
            side_effect=LLMQuotaExceededError(
                "429 RESOURCE_EXHAUSTED: quota exceeded"
            )
        )

        use_case = ReviewCodeUseCase(
            code_review_service=service,
            agent_executor=agent_executor,
        )

        with pytest.raises(LLMQuotaExceededError):
            await use_case.execute(
                repository_id="repo-123",
                user_id="user-abc",
                files_to_review=["src/main.py"],
                review_id=review_id,
            )

        # update_review_status must have been called with FAILED
        calls = service.update_review_status.call_args_list
        statuses_used = [c.args[1] for c in calls if c.args]
        assert ReviewStatusEnum.FAILED in statuses_used, (
            f"Expected FAILED in status updates, got: {statuses_used}"
        )

    @pytest.mark.asyncio
    async def test_quota_error_does_not_call_completed(self):
        review_id = "test-review-uuid-002"
        service = _make_service(review_id)

        agent_executor = MagicMock()
        agent_executor.execute = AsyncMock(
            side_effect=LLMQuotaExceededError("429 RESOURCE_EXHAUSTED")
        )

        use_case = ReviewCodeUseCase(
            code_review_service=service,
            agent_executor=agent_executor,
        )

        with pytest.raises(LLMQuotaExceededError):
            await use_case.execute(
                repository_id="repo-456",
                user_id="user-xyz",
                review_id=review_id,
            )

        calls = service.update_review_status.call_args_list
        completed_calls = [
            c for c in calls
            if c.args and c.args[1] == ReviewStatusEnum.COMPLETED
        ]
        assert not completed_calls, (
            "update_review_status should NOT be called with COMPLETED on quota failure"
        )

    @pytest.mark.asyncio
    async def test_non_quota_error_still_marks_failed(self):
        """A non-quota exception should also result in FAILED (existing behaviour)."""
        review_id = "test-review-uuid-003"
        service = _make_service(review_id)

        agent_executor = MagicMock()
        agent_executor.execute = AsyncMock(
            side_effect=RuntimeError("some other transient error")
        )

        use_case = ReviewCodeUseCase(
            code_review_service=service,
            agent_executor=agent_executor,
        )

        with pytest.raises(RuntimeError):
            await use_case.execute(
                repository_id="repo-789",
                user_id="user-def",
                review_id=review_id,
            )

        calls = service.update_review_status.call_args_list
        statuses_used = [c.args[1] for c in calls if c.args]
        assert ReviewStatusEnum.FAILED in statuses_used
