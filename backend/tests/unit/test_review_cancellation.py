"""
test_review_cancellation.py
============================
Tests for Phase 11.1B-6 Review Cancellation End-to-End.

Covers:
1. Owner cancels pending review (returns 200 OK, status CANCELLED).
2. Owner cancels in-progress review (returns 200 OK, status CANCELLED).
3. User B cancels User A review (returns 404 Not Found, no resource leakage).
4. Unauthenticated cancellation (returns 401 Unauthorized).
5. Unknown review cancellation (returns 404 Not Found).
6. Already cancelled review cancellation (idempotent 200 OK, status CANCELLED).
7. Completed review cancellation (safe response, preserves COMPLETED status).
8. Failed review cancellation (safe response, preserves FAILED status).
9. Cancellation during workflow (stops execution, CANCELLED not overwritten by COMPLETED).
10. Cancellation after AI response before persistence (results discarded, CANCELLED preserved).
11. Progress regression (CANCELLED progress stays < 100%).
12. False-success regression (no heuristic scores or findings generated after cancellation).
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from src.main import app
from src.core.config import settings
from src.domain.entities.code_review import ReviewStatusEnum
from src.application.use_cases.review_code import ReviewCodeUseCase
from src.interfaces.api.dependencies import (
    get_current_user,
    get_agent_use_case,
    get_repository_service,
)
from src.interfaces.api.v1.reviews import get_code_review_service, ACTIVE_REVIEW_TASKS
from src.infrastructure.persistence.code_review_models import DBCodeReview


def _make_db_review(
    review_id: str = "rev_cancel_001",
    user_id: str = "user_a",
    repo_id: str = "repo_a",
    status: str = "in_progress",
    progress_percent: int = 35,
    current_stage: str = "retrieving_context",
    progress_message: str = "Retrieving repository code context…",
) -> DBCodeReview:
    return DBCodeReview(
        id=review_id,
        user_id=user_id,
        repository_id=repo_id,
        status=status,
        progress_percent=progress_percent,
        current_stage=current_stage,
        progress_message=progress_message,
        findings_json=[],
        performance_findings_json=[],
        confidence_score=1.0,
        duration_ms=None,
    )


class TestReviewCancellationAPI:
    """API level test suite for POST /api/v1/reviews/{review_id}/cancel endpoint."""

    def test_1_owner_cancels_pending_review(self):
        """Owner cancels pending review -> 200 OK, status CANCELLED."""
        user_a_id = "user_a_123"
        review_id = "rev_pending_001"
        db_review = _make_db_review(review_id=review_id, user_id=user_a_id, status="pending", progress_percent=0)

        mock_service = MagicMock()
        mock_service.get_review.return_value = db_review

        def mock_update(rid, status, **kwargs):
            db_review.status = status.value if hasattr(status, "value") else status
            if "current_stage" in kwargs:
                db_review.current_stage = kwargs["current_stage"]
            return db_review

        mock_service.update_review_status.side_effect = mock_update

        app.dependency_overrides[get_current_user] = lambda: {"sub": user_a_id}
        app.dependency_overrides[get_code_review_service] = lambda: mock_service

        client = TestClient(app)
        res = client.post(f"/api/v1/reviews/{review_id}/cancel")

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "cancelled"
        assert data["review_id"] == review_id

        app.dependency_overrides.clear()

    def test_2_owner_cancels_in_progress_review(self):
        """Owner cancels in-progress review -> 200 OK, status CANCELLED."""
        user_a_id = "user_a_123"
        review_id = "rev_in_prog_002"
        db_review = _make_db_review(review_id=review_id, user_id=user_a_id, status="in_progress", progress_percent=40)

        mock_service = MagicMock()
        mock_service.get_review.return_value = db_review

        def mock_update(rid, status, **kwargs):
            db_review.status = status.value if hasattr(status, "value") else status
            return db_review

        mock_service.update_review_status.side_effect = mock_update

        app.dependency_overrides[get_current_user] = lambda: {"sub": user_a_id}
        app.dependency_overrides[get_code_review_service] = lambda: mock_service

        client = TestClient(app)
        res = client.post(f"/api/v1/reviews/{review_id}/cancel")

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "cancelled"

        app.dependency_overrides.clear()

    def test_3_user_b_cancels_user_a_review_returns_404(self):
        """User B attempts to cancel User A's review -> 404 Not Found."""
        user_a_id = "user_a_123"
        user_b_id = "user_b_456"
        review_id = "rev_owner_a"
        db_review = _make_db_review(review_id=review_id, user_id=user_a_id)

        mock_service = MagicMock()

        def get_review_side_effect(rid, user_id=None):
            if rid == review_id and user_id == user_a_id:
                return db_review
            return None

        mock_service.get_review.side_effect = get_review_side_effect

        app.dependency_overrides[get_current_user] = lambda: {"sub": user_b_id}
        app.dependency_overrides[get_code_review_service] = lambda: mock_service

        client = TestClient(app)
        res = client.post(f"/api/v1/reviews/{review_id}/cancel")

        assert res.status_code == 404
        assert res.json()["detail"] == "Review not found"

        app.dependency_overrides.clear()

    def test_4_unauthenticated_cancellation_returns_401(self):
        """Unauthenticated cancel request -> 401 Unauthorized."""
        app.dependency_overrides.clear()
        original_bypass = settings.DEV_AUTH_BYPASS
        settings.DEV_AUTH_BYPASS = False

        try:
            client = TestClient(app)
            res = client.post("/api/v1/reviews/rev_test_123/cancel")
            assert res.status_code == 401
        finally:
            settings.DEV_AUTH_BYPASS = original_bypass

    def test_5_unknown_review_cancellation_returns_404(self):
        """Unknown review ID -> 404 Not Found."""
        mock_service = MagicMock()
        mock_service.get_review.return_value = None

        app.dependency_overrides[get_current_user] = lambda: {"sub": "user_a"}
        app.dependency_overrides[get_code_review_service] = lambda: mock_service

        client = TestClient(app)
        res = client.post("/api/v1/reviews/unknown_id_000/cancel")

        assert res.status_code == 404
        assert res.json()["detail"] == "Review not found"

        app.dependency_overrides.clear()

    def test_6_already_cancelled_review_is_idempotent(self):
        """Already cancelled review -> safe 200 OK idempotent response."""
        user_a_id = "user_a_123"
        review_id = "rev_already_cancelled"
        db_review = _make_db_review(review_id=review_id, user_id=user_a_id, status="cancelled", progress_percent=40)

        mock_service = MagicMock()
        mock_service.get_review.return_value = db_review

        app.dependency_overrides[get_current_user] = lambda: {"sub": user_a_id}
        app.dependency_overrides[get_code_review_service] = lambda: mock_service

        client = TestClient(app)
        res = client.post(f"/api/v1/reviews/{review_id}/cancel")

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "cancelled"
        mock_service.update_review_status.assert_not_called()

        app.dependency_overrides.clear()

    def test_7_completed_review_cancellation_is_safe(self):
        """Completed review cancellation -> safe response, retains COMPLETED status."""
        user_a_id = "user_a_123"
        review_id = "rev_completed"
        db_review = _make_db_review(review_id=review_id, user_id=user_a_id, status="completed", progress_percent=100)

        mock_service = MagicMock()
        mock_service.get_review.return_value = db_review

        app.dependency_overrides[get_current_user] = lambda: {"sub": user_a_id}
        app.dependency_overrides[get_code_review_service] = lambda: mock_service

        client = TestClient(app)
        res = client.post(f"/api/v1/reviews/{review_id}/cancel")

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        mock_service.update_review_status.assert_not_called()

        app.dependency_overrides.clear()

    def test_8_failed_review_cancellation_is_safe(self):
        """Failed review cancellation -> safe response, retains FAILED status."""
        user_a_id = "user_a_123"
        review_id = "rev_failed"
        db_review = _make_db_review(review_id=review_id, user_id=user_a_id, status="failed", progress_percent=50)

        mock_service = MagicMock()
        mock_service.get_review.return_value = db_review

        app.dependency_overrides[get_current_user] = lambda: {"sub": user_a_id}
        app.dependency_overrides[get_code_review_service] = lambda: mock_service

        client = TestClient(app)
        res = client.post(f"/api/v1/reviews/{review_id}/cancel")

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "failed"
        mock_service.update_review_status.assert_not_called()

        app.dependency_overrides.clear()


class TestReviewCancellationWorkflow:
    """Workflow level test suite for cancellation during execution and race protection."""

    @pytest.mark.asyncio
    async def test_9_cancellation_during_workflow_prevents_completed_overwrite(self):
        """Workflow execution detects CANCELLED status and stops without calling COMPLETED."""
        review_id = "rev_workflow_cancel"
        fake_review = _make_db_review(review_id=review_id, status="in_progress")

        service = MagicMock()
        service.get_review.return_value = fake_review

        def mock_update(rid, status, **kwargs):
            # Simulate terminal lock: if status is CANCELLED, ignore non-cancelled updates
            if fake_review.status == "cancelled" and status != ReviewStatusEnum.CANCELLED:
                return fake_review
            fake_review.status = status.value if hasattr(status, "value") else status
            return fake_review

        service.update_review_status.side_effect = mock_update

        mock_executor = MagicMock()

        async def fake_execute(query, repo_id, user_id, review_config, on_progress):
            await on_progress("planning", 20, "Planning...")
            # Simulate cancellation occurring while AI is running
            fake_review.status = "cancelled"
            await on_progress("reviewing", 50, "Reviewing...")
            return {"agent_outputs": {}, "confidence_score": 0.9}

        mock_executor.execute = AsyncMock(side_effect=fake_execute)

        use_case = ReviewCodeUseCase(
            code_review_service=service,
            agent_executor=mock_executor,
        )

        res = await use_case.execute(
            repository_id="repo_1",
            user_id="user_1",
            review_id=review_id,
        )

        assert res["status"] == "cancelled"
        assert fake_review.status == "cancelled"

    @pytest.mark.asyncio
    async def test_10_cancellation_after_ai_response_before_persistence_discards_results(self):
        """If review is cancelled right after AI returns but before DB update, results are discarded."""
        review_id = "rev_race_cancel"
        fake_review = _make_db_review(review_id=review_id, status="in_progress")

        service = MagicMock()
        service.get_review.return_value = fake_review

        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(return_value={
            "agent_outputs": {
                "code_review": {"structured_findings": [{"issue": "Unsaved finding", "severity": "high", "explanation": "x"}]}
            },
            "confidence_score": 0.9,
        })

        # Cancel review before execute returns to use_case persistence block
        fake_review.status = "cancelled"

        use_case = ReviewCodeUseCase(
            code_review_service=service,
            agent_executor=mock_executor,
        )

        res = await use_case.execute(
            repository_id="repo_1",
            user_id="user_1",
            review_id=review_id,
        )

        assert res["status"] == "cancelled"
        assert res["findings"] == []
        assert fake_review.status == "cancelled"

    @pytest.mark.asyncio
    async def test_11_progress_remains_below_100_on_cancellation(self):
        """Cancelled review progress percent stays < 100%."""
        review_id = "rev_progress_check"
        fake_review = _make_db_review(review_id=review_id, status="in_progress", progress_percent=40)

        service = MagicMock()
        service.get_review.return_value = fake_review

        def mock_update(rid, status, progress_percent=None, **kwargs):
            if fake_review.status == "cancelled" and status != ReviewStatusEnum.CANCELLED:
                return fake_review
            if status == ReviewStatusEnum.CANCELLED and progress_percent is not None:
                fake_review.progress_percent = progress_percent
            fake_review.status = status.value if hasattr(status, "value") else status
            return fake_review

        service.update_review_status.side_effect = mock_update

        mock_executor = MagicMock()
        fake_review.status = "cancelled"

        use_case = ReviewCodeUseCase(
            code_review_service=service,
            agent_executor=mock_executor,
        )

        res = await use_case.execute(
            repository_id="repo_1",
            user_id="user_1",
            review_id=review_id,
        )

        assert res["status"] == "cancelled"
        assert fake_review.progress_percent < 100

    @pytest.mark.asyncio
    async def test_12_no_heuristic_scores_written_after_cancellation(self):
        """No findings, heuristic scores, or performance numbers are persisted when cancelled."""
        review_id = "rev_no_heuristics"
        fake_review = _make_db_review(review_id=review_id, status="in_progress")

        service = MagicMock()
        service.get_review.return_value = fake_review
        fake_review.status = "cancelled"

        mock_executor = MagicMock()

        use_case = ReviewCodeUseCase(
            code_review_service=service,
            agent_executor=mock_executor,
        )

        res = await use_case.execute(
            repository_id="repo_1",
            user_id="user_1",
            review_id=review_id,
        )

        assert res["status"] == "cancelled"
        # Check that update_review_status was never called with COMPLETED or heuristic scores
        completed_calls = [
            c for c in service.update_review_status.call_args_list
            if c.args and c.args[1] == ReviewStatusEnum.COMPLETED
        ]
        assert not completed_calls
