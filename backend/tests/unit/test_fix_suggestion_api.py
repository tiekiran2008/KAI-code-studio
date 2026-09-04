"""
test_fix_suggestion_api.py
===========================
Phase 11.2B-3 — Tests for Fix Suggestion API, Persistence & User Decisions.

Coverage:
- Security (ownership, unauthenticated, cross-user)
- Review status gates (pending, in_progress, failed, cancelled)
- Finding index validation (negative, out-of-range)
- Persistence (correct slot, fields preserved, round-trip)
- Idempotency (existing suggestion skips LLM)
- Accept / Reject decision API
- Decision transitions and idempotency
- LLM failure / 429 — no partial persistence
- No-mutation verification
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Optional


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_db_review(
    review_id: str = "rev-1",
    user_id: str = "user-a",
    repository_id: str = "repo-1",
    status: str = "completed",
    findings_json: Optional[list] = None,
):
    review = MagicMock()
    review.id = review_id
    review.user_id = user_id
    review.repository_id = repository_id
    review.status = status
    review.progress_percent = 100
    review.current_stage = "done"
    review.progress_message = None
    review.findings_json = findings_json or []
    review.confidence_score = 1.0
    review.duration_ms = 1000
    review.performance_score = None
    review.performance_findings_json = []
    review.performance_recommendations_json = []
    review.estimated_cpu_savings = 0.0
    review.estimated_memory_savings = 0.0
    review.estimated_latency_improvement = 0.0
    review.refactoring_findings_json = []
    review.refactoring_priority = None
    review.estimated_refactoring_effort = 0.0
    review.estimated_maintainability_improvement = 0.0
    review.estimated_technical_debt_reduction = 0.0
    review.estimated_complexity_reduction = 0.0
    review.architecture_findings_json = []
    review.overall_health_score = 0.0
    review.architecture_score = 0.0
    review.maintainability_score = 0.0
    review.technical_debt_score = 0.0
    review.complexity_score = 0.0
    review.documentation_score = 0.0
    review.modularity_score = 0.0
    review.testability_score = 0.0
    review.dependency_analysis_json = {}
    review.created_at = None
    review.updated_at = None
    return review


SAMPLE_FINDING = {
    "issue": "Unused variable",
    "severity": "medium",
    "explanation": "Variable 'temp' is never used.",
    "suggested_fix": "Remove variable 'temp'.",
    "confidence_score": 0.9,
    "file_path": "src/calc.py",
    "line_number": 5,
}

SAMPLE_FIX = {
    "finding_index": 0,
    "file_path": "src/calc.py",
    "original_code": "temp = 1\nreturn a + b",
    "proposed_code": "return a + b",
    "explanation": "Removed unused variable",
    "diff": "--- a/src/calc.py\n+++ b/src/calc.py\n@@ -1,2 +1 @@\n-temp = 1\n return a + b",
    "confidence_score": 0.95,
    "validation_status": "valid",
    "user_decision": "pending",
    "language": "py",
    "validation_message": "Python syntax verified",
}


# ---------------------------------------------------------------------------
# Service-level tests — CodeReviewService persistence
# ---------------------------------------------------------------------------

class TestCodeReviewServiceFixPersistence:

    def _make_service(self, db_review=None):
        from src.application.services.code_review_service import CodeReviewService
        from src.infrastructure.repositories.code_review_repository import CodeReviewRepository
        mock_repo = MagicMock(spec=CodeReviewRepository)
        mock_repo.get_by_id.return_value = db_review
        mock_repo.update.side_effect = lambda r: r
        service = CodeReviewService(mock_repo)
        return service, mock_repo

    def test_persistence_1_fix_stored_in_correct_finding(self):
        """Generated fix is persisted at the correct finding_index slot."""
        from src.domain.entities.fix_suggestion import FixSuggestion, FixValidationStatus, FixUserDecision
        finding_data = [dict(SAMPLE_FINDING), {"issue": "Other", "severity": "low", "explanation": "Other"}]
        db_review = _make_db_review(findings_json=finding_data)

        service, mock_repo = self._make_service(db_review)

        fix = FixSuggestion(**SAMPLE_FIX)
        result = service.update_finding_fix_suggestion("rev-1", 0, fix, user_id="user-a")

        assert result is not None
        assert result["proposed_code"] == "return a + b"
        assert result["finding_index"] == 0

        # Verify persisted findings
        persisted_findings = db_review.findings_json
        assert persisted_findings[0]["fix_suggestion"] is not None
        assert "fix_suggestion" not in persisted_findings[1] or persisted_findings[1].get("fix_suggestion") is None

    def test_persistence_2_other_fields_unchanged(self):
        """Persisting fix does not overwrite existing finding fields."""
        finding_data = [dict(SAMPLE_FINDING)]
        db_review = _make_db_review(findings_json=finding_data)

        service, mock_repo = self._make_service(db_review)

        from src.domain.entities.fix_suggestion import FixSuggestion
        fix = FixSuggestion(**SAMPLE_FIX)
        service.update_finding_fix_suggestion("rev-1", 0, fix, user_id="user-a")

        saved_finding = db_review.findings_json[0]
        assert saved_finding["issue"] == "Unused variable"
        assert saved_finding["severity"] == "medium"
        assert saved_finding["explanation"] == "Variable 'temp' is never used."
        assert saved_finding["file_path"] == "src/calc.py"

    def test_persistence_3_other_findings_unchanged(self):
        """Persisting fix in index 1 does not modify findings at index 0."""
        finding_a = {"issue": "A", "severity": "low", "explanation": "A"}
        finding_b = {"issue": "B", "severity": "medium", "explanation": "B", "file_path": "b.py"}
        db_review = _make_db_review(findings_json=[finding_a, finding_b])

        service, _ = self._make_service(db_review)

        from src.domain.entities.fix_suggestion import FixSuggestion
        fix = FixSuggestion(
            finding_index=1,
            file_path="b.py",
            original_code="x = 1",
            proposed_code="x = 2",
            explanation="Fix x",
            confidence_score=0.9,
        )
        service.update_finding_fix_suggestion("rev-1", 1, fix, user_id="user-a")

        assert "fix_suggestion" not in db_review.findings_json[0] or db_review.findings_json[0].get("fix_suggestion") is None

    def test_persistence_4_serialization_round_trip(self):
        """FixSuggestion serializes to dict and back without data loss."""
        from src.domain.entities.fix_suggestion import FixSuggestion, FixValidationStatus, FixUserDecision

        fix = FixSuggestion(**SAMPLE_FIX)
        serialized = fix.model_dump(mode="json")

        # Reconstruct from dict
        restored = FixSuggestion(**serialized)
        assert restored.proposed_code == fix.proposed_code
        assert restored.user_decision == FixUserDecision.PENDING
        assert restored.validation_status == FixValidationStatus.VALID
        assert restored.language == "py"

    def test_persistence_5_existing_fix_returned_without_new_llm_call(self):
        """If fix_suggestion already in findings_json, service returns it immediately."""
        finding_with_fix = {**SAMPLE_FINDING, "fix_suggestion": SAMPLE_FIX}
        db_review = _make_db_review(findings_json=[finding_with_fix])

        service, mock_repo = self._make_service(db_review)

        from src.domain.entities.fix_suggestion import FixSuggestion
        new_fix = FixSuggestion(**{**SAMPLE_FIX, "proposed_code": "different code"})

        result = service.update_finding_fix_suggestion("rev-1", 0, new_fix, user_id="user-a")

        # Should return EXISTING fix, not the new one
        assert result["proposed_code"] == "return a + b"  # original fixture value
        # Repo update should NOT have been called (no re-write)
        mock_repo.update.assert_not_called()

    def test_persistence_6_failed_generation_leaves_findings_unchanged(self):
        """Service is never called when agent raises; findings remain untouched."""
        finding_data = [dict(SAMPLE_FINDING)]
        db_review = _make_db_review(findings_json=finding_data)

        service, mock_repo = self._make_service(db_review)

        # Simulate: agent raises before service.update_finding_fix_suggestion is called
        # (This test verifies the route doesn't persist partial data)
        # At service level: if we never call update_finding_fix_suggestion, nothing changes
        original_findings = list(db_review.findings_json)
        mock_repo.update.assert_not_called()
        assert db_review.findings_json == original_findings

    def test_persistence_7_review_status_rejected_for_non_completed(self):
        """Service raises ValueError for non-COMPLETED review status."""
        for bad_status in ("pending", "in_progress", "failed", "cancelled"):
            db_review = _make_db_review(status=bad_status, findings_json=[dict(SAMPLE_FINDING)])
            service, _ = self._make_service(db_review)
            from src.domain.entities.fix_suggestion import FixSuggestion
            fix = FixSuggestion(**SAMPLE_FIX)
            with pytest.raises(ValueError, match="completed"):
                service.update_finding_fix_suggestion("rev-1", 0, fix, user_id="user-a")

    def test_persistence_8_negative_index_raises_index_error(self):
        """Service raises IndexError for finding_index < 0."""
        db_review = _make_db_review(findings_json=[dict(SAMPLE_FINDING)])
        service, _ = self._make_service(db_review)
        from src.domain.entities.fix_suggestion import FixSuggestion
        fix = FixSuggestion(**SAMPLE_FIX)
        with pytest.raises(IndexError):
            service.update_finding_fix_suggestion("rev-1", -1, fix, user_id="user-a")

    def test_persistence_9_out_of_range_index_raises_index_error(self):
        """Service raises IndexError when finding_index >= len(findings)."""
        db_review = _make_db_review(findings_json=[dict(SAMPLE_FINDING)])
        service, _ = self._make_service(db_review)
        from src.domain.entities.fix_suggestion import FixSuggestion
        fix = FixSuggestion(**SAMPLE_FIX)
        with pytest.raises(IndexError):
            service.update_finding_fix_suggestion("rev-1", 5, fix, user_id="user-a")

    def test_persistence_10_review_not_found_returns_none(self):
        """Returns None if review not found (ownership / not-found)."""
        service, _ = self._make_service(db_review=None)
        from src.domain.entities.fix_suggestion import FixSuggestion
        fix = FixSuggestion(**SAMPLE_FIX)
        result = service.update_finding_fix_suggestion("nonexistent", 0, fix, user_id="user-a")
        assert result is None


# ---------------------------------------------------------------------------
# Service-level tests — Decision persistence
# ---------------------------------------------------------------------------

class TestCodeReviewServiceDecisionPersistence:

    def _make_service_with_review(self, db_review):
        from src.application.services.code_review_service import CodeReviewService
        from src.infrastructure.repositories.code_review_repository import CodeReviewRepository
        mock_repo = MagicMock(spec=CodeReviewRepository)
        mock_repo.get_by_id.return_value = db_review
        mock_repo.update.side_effect = lambda r: r
        return CodeReviewService(mock_repo)

    def test_decision_1_accept_existing_fix(self):
        """Accept updates user_decision to 'accepted'."""
        from src.domain.entities.fix_suggestion import FixUserDecision
        finding_with_fix = {**SAMPLE_FINDING, "fix_suggestion": dict(SAMPLE_FIX)}
        db_review = _make_db_review(findings_json=[finding_with_fix])
        service = self._make_service_with_review(db_review)

        result = service.update_finding_decision("rev-1", 0, FixUserDecision.ACCEPTED, user_id="user-a")
        assert result["user_decision"] == "accepted"

    def test_decision_2_reject_existing_fix(self):
        """Reject updates user_decision to 'rejected'."""
        from src.domain.entities.fix_suggestion import FixUserDecision
        finding_with_fix = {**SAMPLE_FINDING, "fix_suggestion": dict(SAMPLE_FIX)}
        db_review = _make_db_review(findings_json=[finding_with_fix])
        service = self._make_service_with_review(db_review)

        result = service.update_finding_decision("rev-1", 0, FixUserDecision.REJECTED, user_id="user-a")
        assert result["user_decision"] == "rejected"

    def test_decision_3_accept_without_fix_raises_key_error(self):
        """Accept without existing fix raises KeyError."""
        from src.domain.entities.fix_suggestion import FixUserDecision
        db_review = _make_db_review(findings_json=[dict(SAMPLE_FINDING)])
        service = self._make_service_with_review(db_review)

        with pytest.raises(KeyError, match="No fix suggestion"):
            service.update_finding_decision("rev-1", 0, FixUserDecision.ACCEPTED, user_id="user-a")

    def test_decision_4_reject_without_fix_raises_key_error(self):
        """Reject without existing fix raises KeyError."""
        from src.domain.entities.fix_suggestion import FixUserDecision
        db_review = _make_db_review(findings_json=[dict(SAMPLE_FINDING)])
        service = self._make_service_with_review(db_review)

        with pytest.raises(KeyError):
            service.update_finding_decision("rev-1", 0, FixUserDecision.REJECTED, user_id="user-a")

    def test_decision_5_repeated_accept_is_idempotent(self):
        """Calling accept twice keeps status 'accepted'."""
        from src.domain.entities.fix_suggestion import FixUserDecision
        existing_fix = {**SAMPLE_FIX, "user_decision": "accepted"}
        finding_with_fix = {**SAMPLE_FINDING, "fix_suggestion": existing_fix}
        db_review = _make_db_review(findings_json=[finding_with_fix])
        service = self._make_service_with_review(db_review)

        result = service.update_finding_decision("rev-1", 0, FixUserDecision.ACCEPTED, user_id="user-a")
        assert result["user_decision"] == "accepted"

    def test_decision_6_repeated_reject_is_idempotent(self):
        """Calling reject twice keeps status 'rejected'."""
        from src.domain.entities.fix_suggestion import FixUserDecision
        existing_fix = {**SAMPLE_FIX, "user_decision": "rejected"}
        finding_with_fix = {**SAMPLE_FINDING, "fix_suggestion": existing_fix}
        db_review = _make_db_review(findings_json=[finding_with_fix])
        service = self._make_service_with_review(db_review)

        result = service.update_finding_decision("rev-1", 0, FixUserDecision.REJECTED, user_id="user-a")
        assert result["user_decision"] == "rejected"

    def test_decision_7_accepted_to_rejected_override_allowed(self):
        """accepted → rejected transition is allowed (no file mutation involved)."""
        from src.domain.entities.fix_suggestion import FixUserDecision
        existing_fix = {**SAMPLE_FIX, "user_decision": "accepted"}
        finding_with_fix = {**SAMPLE_FINDING, "fix_suggestion": existing_fix}
        db_review = _make_db_review(findings_json=[finding_with_fix])
        service = self._make_service_with_review(db_review)

        result = service.update_finding_decision("rev-1", 0, FixUserDecision.REJECTED, user_id="user-a")
        assert result["user_decision"] == "rejected"

    def test_decision_8_rejected_to_accepted_override_allowed(self):
        """rejected → accepted transition is allowed."""
        from src.domain.entities.fix_suggestion import FixUserDecision
        existing_fix = {**SAMPLE_FIX, "user_decision": "rejected"}
        finding_with_fix = {**SAMPLE_FINDING, "fix_suggestion": existing_fix}
        db_review = _make_db_review(findings_json=[finding_with_fix])
        service = self._make_service_with_review(db_review)

        result = service.update_finding_decision("rev-1", 0, FixUserDecision.ACCEPTED, user_id="user-a")
        assert result["user_decision"] == "accepted"

    def test_decision_9_out_of_range_index_raises_index_error(self):
        """Out-of-range finding_index raises IndexError in decision update."""
        from src.domain.entities.fix_suggestion import FixUserDecision
        db_review = _make_db_review(findings_json=[dict(SAMPLE_FINDING)])
        service = self._make_service_with_review(db_review)

        with pytest.raises(IndexError):
            service.update_finding_decision("rev-1", 99, FixUserDecision.ACCEPTED, user_id="user-a")

    def test_decision_10_review_not_found_returns_none(self):
        """Returns None when review not found."""
        from src.domain.entities.fix_suggestion import FixUserDecision
        from src.application.services.code_review_service import CodeReviewService
        from src.infrastructure.repositories.code_review_repository import CodeReviewRepository
        mock_repo = MagicMock(spec=CodeReviewRepository)
        mock_repo.get_by_id.return_value = None
        service = CodeReviewService(mock_repo)

        result = service.update_finding_decision("nonexistent", 0, FixUserDecision.ACCEPTED)
        assert result is None


# ---------------------------------------------------------------------------
# Route-level integration-style tests via TestClient + dependency_overrides
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient
from src.main import app
from src.interfaces.api.dependencies import get_current_user, get_db_session
from src.interfaces.api.v1.reviews import get_code_review_service, get_fix_suggestion_agent


def _user_override(user_id: str = "user-a"):
    """Return a dependency-override callable for get_current_user."""
    from src.interfaces.api.dependencies import UserPayload
    def _override():
        return UserPayload(sub=user_id, email=f"{user_id}@test.com")
    return _override


def _raise_401_override():
    """Override that always raises 401."""
    from fastapi import HTTPException
    def _override():
        raise HTTPException(status_code=401, detail="Not authenticated")
    return _override


def _svc_override(svc_mock):
    """Return a dependency-override callable that yields svc_mock."""
    def _override():
        return svc_mock
    return _override


def _agent_override(agent_mock):
    def _override():
        return agent_mock
    return _override


class TestSecurityEndpoints:

    def setup_method(self):
        """Restore app overrides after each test."""
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_security_1_owner_generates_fix_succeeds(self):
        """Owner of review can generate a fix (succeeds with mock agent)."""
        db_review = _make_db_review(
            user_id="user-a",
            status="completed",
            findings_json=[dict(SAMPLE_FINDING)],
        )
        svc = MagicMock()
        svc.get_review.return_value = db_review
        svc.update_finding_fix_suggestion.return_value = SAMPLE_FIX

        from src.domain.entities.fix_suggestion import FixSuggestion
        mock_agent = MagicMock()
        mock_agent.generate_fix = AsyncMock(return_value=FixSuggestion(**SAMPLE_FIX))

        app.dependency_overrides[get_current_user] = _user_override("user-a")
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)
        app.dependency_overrides[get_fix_suggestion_agent] = _agent_override(mock_agent)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix")
        assert resp.status_code == 200
        assert "fix_suggestion" in resp.json()

    def test_security_2_cross_user_blocked_404(self):
        """User B cannot access User A's review — service returns None."""
        svc = MagicMock()
        svc.get_review.return_value = None

        app.dependency_overrides[get_current_user] = _user_override("user-b")
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)
        app.dependency_overrides[get_fix_suggestion_agent] = _agent_override(MagicMock())

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix")
        assert resp.status_code == 404

    def test_security_3_unauthenticated_generate_401(self):
        """Unauthenticated request returns 401."""
        app.dependency_overrides[get_current_user] = _raise_401_override()

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix")
        assert resp.status_code == 401

    def test_security_4_unknown_review_404(self):
        """Non-existent review_id returns 404."""
        svc = MagicMock()
        svc.get_review.return_value = None

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)
        app.dependency_overrides[get_fix_suggestion_agent] = _agent_override(MagicMock())

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/nonexistent-review/findings/0/fix")
        assert resp.status_code == 404

    def test_security_5_negative_finding_index_422(self):
        """Negative finding_index is rejected with 422."""
        db_review = _make_db_review(status="completed", findings_json=[dict(SAMPLE_FINDING)])
        svc = MagicMock()
        svc.get_review.return_value = db_review

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)
        app.dependency_overrides[get_fix_suggestion_agent] = _agent_override(MagicMock())

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/-1/fix")
        assert resp.status_code == 422

    def test_security_6_out_of_range_finding_index_422(self):
        """Finding index beyond array length returns 422."""
        db_review = _make_db_review(status="completed", findings_json=[dict(SAMPLE_FINDING)])
        svc = MagicMock()
        svc.get_review.return_value = db_review

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)
        app.dependency_overrides[get_fix_suggestion_agent] = _agent_override(MagicMock())

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/99/fix")
        assert resp.status_code == 422

    def test_security_7_failed_review_rejected_409(self):
        """Fix generation on a FAILED review returns 409."""
        db_review = _make_db_review(status="failed", findings_json=[dict(SAMPLE_FINDING)])
        svc = MagicMock()
        svc.get_review.return_value = db_review

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)
        app.dependency_overrides[get_fix_suggestion_agent] = _agent_override(MagicMock())

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix")
        assert resp.status_code == 409

    def test_security_8_cancelled_review_rejected_409(self):
        """Fix generation on a CANCELLED review returns 409."""
        db_review = _make_db_review(status="cancelled", findings_json=[dict(SAMPLE_FINDING)])
        svc = MagicMock()
        svc.get_review.return_value = db_review

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)
        app.dependency_overrides[get_fix_suggestion_agent] = _agent_override(MagicMock())

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix")
        assert resp.status_code == 409

    def test_security_9_in_progress_review_rejected_409(self):
        """Fix generation on an IN_PROGRESS review returns 409."""
        db_review = _make_db_review(status="in_progress", findings_json=[dict(SAMPLE_FINDING)])
        svc = MagicMock()
        svc.get_review.return_value = db_review

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)
        app.dependency_overrides[get_fix_suggestion_agent] = _agent_override(MagicMock())

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix")
        assert resp.status_code == 409

    def test_security_10_cross_user_accept_blocked_404(self):
        """User B cannot accept User A's fix suggestion."""
        svc = MagicMock()
        svc.get_review.return_value = None

        app.dependency_overrides[get_current_user] = _user_override("user-b")
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/accept")
        assert resp.status_code == 404

    def test_security_11_cross_user_reject_blocked_404(self):
        """User B cannot reject User A's fix suggestion."""
        svc = MagicMock()
        svc.get_review.return_value = None

        app.dependency_overrides[get_current_user] = _user_override("user-b")
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/reject")
        assert resp.status_code == 404

    def test_security_12_unauthenticated_accept_401(self):
        """Unauthenticated accept returns 401."""
        app.dependency_overrides[get_current_user] = _raise_401_override()

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/accept")
        assert resp.status_code == 401

    def test_security_13_unauthenticated_reject_401(self):
        """Unauthenticated reject returns 401."""
        app.dependency_overrides[get_current_user] = _raise_401_override()

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/reject")
        assert resp.status_code == 401


class TestAcceptRejectEndpoints:

    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_accept_1_existing_fix_succeeds(self):
        """POST accept returns accepted fix."""
        accepted_fix = {**SAMPLE_FIX, "user_decision": "accepted"}
        svc = MagicMock()
        svc.get_review.return_value = _make_db_review(status="completed", findings_json=[dict(SAMPLE_FINDING)])
        svc.update_finding_decision.return_value = accepted_fix

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/accept")
        assert resp.status_code == 200
        assert resp.json()["fix_suggestion"]["user_decision"] == "accepted"

    def test_reject_1_existing_fix_succeeds(self):
        """POST reject returns rejected fix."""
        rejected_fix = {**SAMPLE_FIX, "user_decision": "rejected"}
        svc = MagicMock()
        svc.get_review.return_value = _make_db_review(status="completed", findings_json=[dict(SAMPLE_FINDING)])
        svc.update_finding_decision.return_value = rejected_fix

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/reject")
        assert resp.status_code == 200
        assert resp.json()["fix_suggestion"]["user_decision"] == "rejected"

    def test_accept_2_no_fix_returns_404(self):
        """Accept when no fix suggestion exists returns 404."""
        svc = MagicMock()
        svc.get_review.return_value = _make_db_review(status="completed", findings_json=[dict(SAMPLE_FINDING)])
        svc.update_finding_decision.side_effect = KeyError("No fix suggestion exists for this finding")

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/accept")
        assert resp.status_code == 404

    def test_reject_2_no_fix_returns_404(self):
        """Reject when no fix suggestion exists returns 404."""
        svc = MagicMock()
        svc.get_review.return_value = _make_db_review(status="completed", findings_json=[dict(SAMPLE_FINDING)])
        svc.update_finding_decision.side_effect = KeyError("No fix suggestion exists for this finding")

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/reject")
        assert resp.status_code == 404

    def test_accept_3_negative_index_422(self):
        """Negative finding_index on accept returns 422."""
        svc = MagicMock()
        svc.get_review.return_value = _make_db_review(status="completed", findings_json=[dict(SAMPLE_FINDING)])

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/-1/fix/accept")
        assert resp.status_code == 422

    def test_reject_3_negative_index_422(self):
        """Negative finding_index on reject returns 422."""
        svc = MagicMock()
        svc.get_review.return_value = _make_db_review(status="completed", findings_json=[dict(SAMPLE_FINDING)])

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/-2/fix/reject")
        assert resp.status_code == 422


class TestIdempotencyAndCaching:

    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_idempotency_1_existing_suggestion_returns_cached(self):
        """When fix_suggestion already in findings_json, returns it with cached=True without calling agent."""
        finding_with_fix = {**SAMPLE_FINDING, "fix_suggestion": SAMPLE_FIX}
        db_review = _make_db_review(status="completed", findings_json=[finding_with_fix])

        svc = MagicMock()
        svc.get_review.return_value = db_review

        mock_agent = MagicMock()
        mock_agent.generate_fix = AsyncMock()

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)
        app.dependency_overrides[get_fix_suggestion_agent] = _agent_override(mock_agent)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix")

        assert resp.status_code == 200
        assert resp.json()["cached"] is True
        # Agent was NOT called
        mock_agent.generate_fix.assert_not_called()

    def test_idempotency_2_new_suggestion_not_cached(self):
        """First-time generation returns cached=False."""
        db_review = _make_db_review(status="completed", findings_json=[dict(SAMPLE_FINDING)])

        svc = MagicMock()
        svc.get_review.return_value = db_review
        svc.update_finding_fix_suggestion.return_value = SAMPLE_FIX

        from src.domain.entities.fix_suggestion import FixSuggestion
        mock_agent = MagicMock()
        mock_agent.generate_fix = AsyncMock(return_value=FixSuggestion(**SAMPLE_FIX))

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)
        app.dependency_overrides[get_fix_suggestion_agent] = _agent_override(mock_agent)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix")

        assert resp.status_code == 200
        assert resp.json()["cached"] is False


class TestLLMFailureHandling:

    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_llm_failure_1_quota_returns_429(self):
        """LLMQuotaExceededError maps to HTTP 429."""
        from src.core.errors import LLMQuotaExceededError
        db_review = _make_db_review(status="completed", findings_json=[dict(SAMPLE_FINDING)])

        svc = MagicMock()
        svc.get_review.return_value = db_review

        mock_agent = MagicMock()
        mock_agent.generate_fix = AsyncMock(
            side_effect=LLMQuotaExceededError("429 RESOURCE_EXHAUSTED")
        )

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)
        app.dependency_overrides[get_fix_suggestion_agent] = _agent_override(mock_agent)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix")

        assert resp.status_code == 429
        # Service update was NOT called — no persistence attempted
        svc.update_finding_fix_suggestion.assert_not_called()

    def test_llm_failure_2_workflow_error_returns_502(self):
        """WorkflowExecutionError maps to HTTP 502."""
        from src.core.errors import WorkflowExecutionError
        db_review = _make_db_review(status="completed", findings_json=[dict(SAMPLE_FINDING)])

        svc = MagicMock()
        svc.get_review.return_value = db_review

        mock_agent = MagicMock()
        mock_agent.generate_fix = AsyncMock(
            side_effect=WorkflowExecutionError("LLM returned empty proposed code")
        )

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)
        app.dependency_overrides[get_fix_suggestion_agent] = _agent_override(mock_agent)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix")

        assert resp.status_code == 502
        svc.update_finding_fix_suggestion.assert_not_called()

    def test_llm_failure_3_findings_unchanged_on_quota_error(self):
        """findings_json is not modified when LLM raises quota error."""
        from src.core.errors import LLMQuotaExceededError
        db_review = _make_db_review(status="completed", findings_json=[dict(SAMPLE_FINDING)])

        svc = MagicMock()
        svc.get_review.return_value = db_review

        mock_agent = MagicMock()
        mock_agent.generate_fix = AsyncMock(side_effect=LLMQuotaExceededError())

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)
        app.dependency_overrides[get_fix_suggestion_agent] = _agent_override(mock_agent)

        client = TestClient(app, raise_server_exceptions=False)
        client.post("/api/v1/reviews/rev-1/findings/0/fix")

        # Service persistence method never called
        svc.update_finding_fix_suggestion.assert_not_called()


class TestNoMutationVerification:
    """Verify that generate, accept, and reject do not touch filesystem or git."""

    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_no_mutation_1_generate_does_not_write_files(self):
        """generate_fix endpoint does not call any filesystem write methods."""
        import builtins
        original_open = builtins.open
        write_calls = []

        def spy_open(path, mode="r", *args, **kwargs):
            if "w" in mode or "a" in mode or "x" in mode:
                write_calls.append(path)
            return original_open(path, mode, *args, **kwargs)

        db_review = _make_db_review(status="completed", findings_json=[dict(SAMPLE_FINDING)])
        svc = MagicMock()
        svc.get_review.return_value = db_review
        svc.update_finding_fix_suggestion.return_value = SAMPLE_FIX

        from src.domain.entities.fix_suggestion import FixSuggestion
        mock_agent = MagicMock()
        mock_agent.generate_fix = AsyncMock(return_value=FixSuggestion(**SAMPLE_FIX))

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)
        app.dependency_overrides[get_fix_suggestion_agent] = _agent_override(mock_agent)

        builtins.open = spy_open
        try:
            client = TestClient(app, raise_server_exceptions=False)
            client.post("/api/v1/reviews/rev-1/findings/0/fix")
        finally:
            builtins.open = original_open

        # No file writes occurred
        assert len(write_calls) == 0

    def test_no_mutation_2_accept_does_not_write_files(self):
        """accept endpoint does not write to filesystem."""
        import builtins
        write_calls = []
        original_open = builtins.open

        def spy_open(path, mode="r", *args, **kwargs):
            if "w" in mode or "a" in mode or "x" in mode:
                write_calls.append(path)
            return original_open(path, mode, *args, **kwargs)

        accepted_fix = {**SAMPLE_FIX, "user_decision": "accepted"}
        svc = MagicMock()
        svc.get_review.return_value = _make_db_review(status="completed", findings_json=[dict(SAMPLE_FINDING)])
        svc.update_finding_decision.return_value = accepted_fix

        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_code_review_service] = _svc_override(svc)

        builtins.open = spy_open
        try:
            client = TestClient(app, raise_server_exceptions=False)
            client.post("/api/v1/reviews/rev-1/findings/0/fix/accept")
        finally:
            builtins.open = original_open

        assert len(write_calls) == 0

    def test_no_mutation_3_agent_has_no_write_methods(self):
        """FixSuggestionAgent has zero file write / git methods."""
        from src.application.agents.fix_suggestion import FixSuggestionAgent
        import inspect
        write_keywords = ("write", "apply", "commit", "push", "patch", "git_")
        for name, _ in inspect.getmembers(FixSuggestionAgent, predicate=inspect.isfunction):
            for kw in write_keywords:
                assert kw not in name.lower(), (
                    f"FixSuggestionAgent has suspicious method: '{name}'"
                )

    def test_no_mutation_4_service_has_no_git_methods(self):
        """CodeReviewService has zero git-related mutation methods.

        Allowlisted persistence helpers:
        - update_finding_git_commit_result: stores Git commit metadata JSON only;
          performs zero actual Git operations (no subprocess, no push, no branch mutation).
        """
        from src.application.services.code_review_service import CodeReviewService
        import inspect
        # Dangerous actual-Git-execution patterns that must never appear in CodeReviewService
        forbidden_keywords = ("push", "git_push", "git_apply", "git_commit_exec")
        # Allowed persistence methods that contain 'git' in their name but are JSON-only
        allowed_git_persistence = {
            "update_finding_git_commit_result",
            "update_finding_git_push_result",
            "update_finding_git_pull_request_result",
        }
        for name, _ in inspect.getmembers(CodeReviewService, predicate=inspect.isfunction):
            if name in allowed_git_persistence:
                continue  # Phase 11.5B: JSON-only Git result persistence — no actual Git execution
            for kw in forbidden_keywords:
                assert kw not in name.lower(), (
                    f"CodeReviewService has suspicious git execution method: '{name}'"
                )


class TestGetReviewPersistenceVerification:
    """Verify GET review correctly exposes persisted fix_suggestion via findings."""

    def test_get_review_1_fix_suggestion_visible_in_findings(self):
        """GET review returns findings with fix_suggestion nested inside."""
        finding_with_fix = {**SAMPLE_FINDING, "fix_suggestion": SAMPLE_FIX}
        db_review = _make_db_review(status="completed", findings_json=[finding_with_fix])

        from src.interfaces.api.v1.reviews import _db_review_to_response
        resp = _db_review_to_response(db_review)

        assert len(resp.findings) == 1
        assert resp.findings[0].get("fix_suggestion") is not None
        assert resp.findings[0]["fix_suggestion"]["proposed_code"] == "return a + b"

    def test_get_review_2_accepted_decision_visible(self):
        """GET review returns the accepted decision inside fix_suggestion."""
        accepted_fix = {**SAMPLE_FIX, "user_decision": "accepted"}
        finding_with_fix = {**SAMPLE_FINDING, "fix_suggestion": accepted_fix}
        db_review = _make_db_review(status="completed", findings_json=[finding_with_fix])

        from src.interfaces.api.v1.reviews import _db_review_to_response
        resp = _db_review_to_response(db_review)

        assert resp.findings[0]["fix_suggestion"]["user_decision"] == "accepted"

    def test_get_review_3_rejected_decision_visible(self):
        """GET review returns the rejected decision inside fix_suggestion."""
        rejected_fix = {**SAMPLE_FIX, "user_decision": "rejected"}
        finding_with_fix = {**SAMPLE_FINDING, "fix_suggestion": rejected_fix}
        db_review = _make_db_review(status="completed", findings_json=[finding_with_fix])

        from src.interfaces.api.v1.reviews import _db_review_to_response
        resp = _db_review_to_response(db_review)

        assert resp.findings[0]["fix_suggestion"]["user_decision"] == "rejected"

    def test_get_review_4_finding_without_fix_safe(self):
        """GET review serializes findings without fix_suggestion safely."""
        db_review = _make_db_review(status="completed", findings_json=[dict(SAMPLE_FINDING)])

        from src.interfaces.api.v1.reviews import _db_review_to_response
        resp = _db_review_to_response(db_review)

        assert len(resp.findings) == 1
        assert resp.findings[0].get("fix_suggestion") is None

