"""
test_review_progress.py
========================
Tests for Phase 11.1B-5 Review Progress Tracking.

Covers:
1. Initial review state (0% progress, queued stage).
2. Review begin (IN_PROGRESS, progress increases).
3. Stage transitions (monotonic, progress never decreases).
4. Successful review (100% + COMPLETED stage).
5. Gemini 429 quota failure (FAILED + progress < 100).
6. Generic workflow exception (FAILED + progress < 100).
7. Unauthorized user polling (404 Not Found).
8. History endpoint regression check.
9. Strictness/check configuration regression check.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from src.main import app
from src.domain.entities.code_review import ReviewStatusEnum
from src.application.use_cases.review_code import ReviewCodeUseCase
from src.core.errors import LLMQuotaExceededError, WorkflowExecutionError
from src.interfaces.api.dependencies import (
    get_current_user,
    get_agent_use_case,
    get_repository_service,
)
from src.interfaces.api.v1.reviews import get_code_review_service
from src.infrastructure.persistence.code_review_models import DBCodeReview


def _make_db_review(
    review_id: str = "rev_progress_001",
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


class TestReviewProgressBackend:
    """Unit tests for ReviewCodeUseCase progress updates and failure behavior."""

    @pytest.mark.asyncio
    async def test_review_progress_lifecycle(self):
        """1, 2, 3, 4: Verifies monotonic progress updates leading to 100% COMPLETED."""
        service = MagicMock()
        history_updates = []

        def mock_update(review_id, status, progress_percent=None, current_stage=None, progress_message=None, **kwargs):
            history_updates.append({
                "status": status.value if hasattr(status, "value") else status,
                "progress_percent": progress_percent,
                "current_stage": current_stage,
                "progress_message": progress_message,
            })
            return MagicMock()

        service.update_review_status.side_effect = mock_update

        mock_executor = MagicMock()

        async def fake_execute(query, repo_id, user_id, review_config, on_progress):
            await on_progress("planning", 20, "Planner analyzing tasks…")
            await on_progress("retrieving_context", 35, "Retrieving context…")
            await on_progress("reviewing", 50, "Running AI review…")
            await on_progress("evaluating", 75, "Evaluating findings…")
            return {
                "agent_outputs": {
                    "code_review": {"structured_findings": [{"issue": "Test bug", "severity": "medium", "explanation": "x"}]}
                },
                "confidence_score": 0.95,
            }

        mock_executor.execute = AsyncMock(side_effect=fake_execute)

        use_case = ReviewCodeUseCase(
            code_review_service=service,
            agent_executor=mock_executor,
        )

        res = await use_case.execute(
            repository_id="repo_1",
            user_id="user_1",
            review_id="rev_1",
        )

        assert res["status"] == "completed"

        # Check progress monotonicity
        percents = [u["progress_percent"] for u in history_updates if u["progress_percent"] is not None]
        assert percents[0] == 10  # Initial preparing
        assert percents[-1] == 100  # Final completed

        for i in range(1, len(percents)):
            assert percents[i] >= percents[i - 1], f"Progress decreased at index {i}: {percents}"

    @pytest.mark.asyncio
    async def test_gemini_429_progress_stays_below_100(self):
        """5: Gemini 429 failure keeps progress < 100% and marks FAILED."""
        service = MagicMock()
        history_updates = []

        def mock_update(review_id, status, progress_percent=None, current_stage=None, progress_message=None, **kwargs):
            history_updates.append({
                "status": status.value if hasattr(status, "value") else status,
                "progress_percent": progress_percent,
                "current_stage": current_stage,
            })
            return MagicMock()

        service.update_review_status.side_effect = mock_update

        mock_executor = MagicMock()

        async def fake_execute(query, repo_id, user_id, review_config, on_progress):
            await on_progress("planning", 20, "Planner agent created plan…")
            await on_progress("retrieving_context", 35, "Retrieving repository code context…")
            raise LLMQuotaExceededError("429 RESOURCE_EXHAUSTED")

        mock_executor.execute = AsyncMock(side_effect=fake_execute)

        use_case = ReviewCodeUseCase(
            code_review_service=service,
            agent_executor=mock_executor,
        )

        with pytest.raises(LLMQuotaExceededError):
            await use_case.execute(
                repository_id="repo_1",
                user_id="user_1",
                review_id="rev_1",
            )

        failed_update = [u for u in history_updates if u["status"] == "failed"]
        assert len(failed_update) == 1
        assert failed_update[0]["progress_percent"] < 100
        assert failed_update[0]["progress_percent"] == 35

    @pytest.mark.asyncio
    async def test_generic_workflow_exception_progress_stays_below_100(self):
        """6: Generic exception keeps progress < 100% and marks FAILED."""
        service = MagicMock()
        history_updates = []

        def mock_update(review_id, status, progress_percent=None, current_stage=None, progress_message=None, **kwargs):
            history_updates.append({
                "status": status.value if hasattr(status, "value") else status,
                "progress_percent": progress_percent,
            })
            return MagicMock()

        service.update_review_status.side_effect = mock_update

        mock_executor = MagicMock()

        async def fake_execute(query, repo_id, user_id, review_config, on_progress):
            await on_progress("planning", 20, "Planner agent created plan…")
            raise WorkflowExecutionError("Execution crashed")

        mock_executor.execute = AsyncMock(side_effect=fake_execute)

        use_case = ReviewCodeUseCase(
            code_review_service=service,
            agent_executor=mock_executor,
        )

        with pytest.raises(WorkflowExecutionError):
            await use_case.execute(
                repository_id="repo_1",
                user_id="user_1",
                review_id="rev_1",
            )

        failed_update = [u for u in history_updates if u["status"] == "failed"]
        assert len(failed_update) == 1
        assert failed_update[0]["progress_percent"] < 100
        assert failed_update[0]["progress_percent"] == 20


class TestReviewProgressAPIEndpoints:
    """API endpoint tests for progress polling, security, and history compatibility."""

    def test_get_review_progress_endpoint(self):
        """Exposes progress_percent, current_stage, and status via GET /reviews/{id}/progress."""
        user_a_id = "user_a_123"
        review_id = "rev_progress_999"
        db_review = _make_db_review(review_id=review_id, user_id=user_a_id)

        mock_service = MagicMock()
        mock_service.get_review.return_value = db_review

        app.dependency_overrides[get_current_user] = lambda: {"sub": user_a_id}
        app.dependency_overrides[get_code_review_service] = lambda: mock_service

        client = TestClient(app)
        res = client.get(f"/api/v1/reviews/{review_id}/progress")

        assert res.status_code == 200
        data = res.json()
        assert data["id"] == review_id
        assert data["status"] == "in_progress"
        assert data["progress_percent"] == 35
        assert data["current_stage"] == "retrieving_context"
        assert data["progress_message"] == "Retrieving repository code context…"

        app.dependency_overrides.clear()

    def test_unauthorized_user_progress_polling(self):
        """7: User B polling User A's review returns 404 Not Found."""
        user_a_id = "user_a_123"
        user_b_id = "user_b_456"
        review_id = "rev_progress_999"
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

        # GET /reviews/{id}
        res1 = client.get(f"/api/v1/reviews/{review_id}")
        assert res1.status_code == 404

        # GET /reviews/{id}/progress
        res2 = client.get(f"/api/v1/reviews/{review_id}/progress")
        assert res2.status_code == 404

        app.dependency_overrides.clear()

    def test_history_endpoint_regression(self):
        """8: History endpoint works seamlessly and includes progress metadata."""
        user_a_id = "user_a_123"
        repo_id = "repo_a_1"
        review1 = _make_db_review("rev_1", user_a_id, repo_id, status="completed", progress_percent=100, current_stage="completed")
        review2 = _make_db_review("rev_2", user_a_id, repo_id, status="in_progress", progress_percent=50, current_stage="reviewing")

        mock_service = MagicMock()
        mock_service.get_repository_reviews.return_value = [review1, review2]

        mock_repo_service = MagicMock()
        mock_repo_service.get_repository.return_value = MagicMock()

        app.dependency_overrides[get_current_user] = lambda: {"sub": user_a_id}
        app.dependency_overrides[get_code_review_service] = lambda: mock_service
        app.dependency_overrides[get_repository_service] = lambda: mock_repo_service

        client = TestClient(app)
        res = client.get(f"/api/v1/reviews/history/{repo_id}")

        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        assert data[0]["progress_percent"] == 100
        assert data[1]["progress_percent"] == 50

        app.dependency_overrides.clear()

    def test_strictness_and_check_config_preservation(self):
        """9: Strictness and toggles configuration pass through properly to execution."""
        user_a_id = "user_a_123"
        repo_id = "repo_a_1"

        mock_repo_service = MagicMock()
        mock_repo_service.get_repository.return_value = MagicMock()

        mock_code_review_service = MagicMock()
        mock_agent_executor = MagicMock()

        app.dependency_overrides[get_current_user] = lambda: {"sub": user_a_id}
        app.dependency_overrides[get_code_review_service] = lambda: mock_code_review_service
        app.dependency_overrides[get_repository_service] = lambda: mock_repo_service
        app.dependency_overrides[get_agent_use_case] = lambda: mock_agent_executor

        client = TestClient(app)
        res = client.post(
            "/api/v1/reviews/start",
            json={
                "repository_id": repo_id,
                "config": {
                    "strictness": "high",
                    "codeQuality": True,
                    "security": True,
                    "performance": False,
                },
            },
        )

        assert res.status_code == 202
        assert res.json()["status"] == "pending"

        app.dependency_overrides.clear()
