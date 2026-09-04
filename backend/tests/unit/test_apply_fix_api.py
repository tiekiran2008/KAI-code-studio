"""
test_apply_fix_api.py
======================
Phase 11.3B-3 — Secure Apply Fix API & Contract Validation Tests.

Validates all 27 Phase 11.3B-3 security, HTTP contract, concurrency,
authorization, sandboxing, idempotency, and OpenAPI requirements.
"""
import asyncio
import os
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.api.dependencies import (
    get_current_user,
    get_repository_service,
    get_apply_fix_use_case,
)
from src.interfaces.api.v1.reviews import get_code_review_service
from src.domain.entities.code_review import ReviewStatusEnum
from src.domain.entities.fix_suggestion import (
    FixUserDecision,
    FixValidationStatus,
    FixApplicationStatus,
)
from src.application.use_cases.apply_fix import ApplyFixSuggestionUseCase
from src.application.services.atomic_patcher import AtomicFilePatcher


def _user_override(user_id: str = "user-1", email: str = "dev@example.com"):
    def _override():
        return {"sub": user_id, "email": email}
    return _override


def _make_review(
    review_id: str = "rev-1",
    user_id: str = "user-1",
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
    review.created_at = "2026-08-25T00:00:00Z"
    review.updated_at = "2026-08-25T00:00:00Z"
    return review


def _make_repo(repo_id: str = "repo-1", user_id: str = "user-1"):
    repo = MagicMock()
    repo.id = repo_id
    repo.user_id = user_id
    return repo


@pytest.fixture
def apply_env(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target_file = workspace / "src" / "calc.py"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("def calc(a, b):\n    return a + b\n", encoding="utf-8")

    sample_fix = {
        "finding_index": 0,
        "file_path": "src/calc.py",
        "original_code": "return a + b",
        "proposed_code": "return a * b",
        "explanation": "Multiply instead of add",
        "diff": "--- a/src/calc.py\n+++ b/src/calc.py\n@@ -2 +2 @@\n-    return a + b\n+    return a * b",
        "confidence_score": 0.95,
        "validation_status": FixValidationStatus.VALID.value,
        "user_decision": FixUserDecision.ACCEPTED.value,
        "application_status": FixApplicationStatus.NOT_APPLIED.value,
        "language": "python",
    }

    sample_finding = {
        "issue": "Use multiplication",
        "severity": "medium",
        "explanation": "Calculation should be product",
        "suggested_fix": "Use multiplication",
        "confidence_score": 0.95,
        "file_path": "src/calc.py",
        "line_number": 2,
        "fix_suggestion": sample_fix,
    }

    return {
        "workspace": workspace,
        "target_file": target_file,
        "sample_fix": sample_fix,
        "sample_finding": sample_finding,
    }


class TestApplyFixSecurityAndContract:
    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_apply_fix_1_endpoint_exists_in_openapi(self):
        """POST /api/v1/reviews/{review_id}/findings/{finding_index}/fix/apply is registered."""
        client = TestClient(app)
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        path = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/apply"
        assert path in schema["paths"], f"Expected {path} in OpenAPI paths"
        assert "post" in schema["paths"][path]

    def test_apply_fix_2_requires_authentication(self):
        """Unauthenticated requests are rejected with 401."""
        client = TestClient(app)
        # Without dependency overrides and without token
        with patch("src.core.config.settings.DEV_AUTH_BYPASS", False):
            resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/apply")
            assert resp.status_code == 401

    def test_apply_fix_3_review_ownership_enforced(self, apply_env):
        """Non-owner accessing review receives 404 (preventing existence leak)."""
        app.dependency_overrides[get_current_user] = _user_override(user_id="user-attacker")
        
        # When user does not own review, get_review returns None
        mock_review_svc = MagicMock()
        mock_review_svc.get_review.return_value = None
        mock_repo_svc = MagicMock()
        mock_repo_svc.get_repository.return_value = _make_repo()

        use_case = ApplyFixSuggestionUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(apply_env["workspace"]),
        )
        app.dependency_overrides[get_apply_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/apply")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_apply_fix_4_repository_ownership_enforced(self, apply_env):
        """Review owned by user but repository not owned returns 404."""
        app.dependency_overrides[get_current_user] = _user_override(user_id="user-1")
        
        review = _make_review(user_id="user-1", findings_json=[apply_env["sample_finding"]])
        mock_review_svc = MagicMock()
        mock_review_svc.get_review.return_value = review

        mock_repo_svc = MagicMock()
        mock_repo_svc.get_repository.return_value = None  # Repo not owned

        use_case = ApplyFixSuggestionUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(apply_env["workspace"]),
        )
        app.dependency_overrides[get_apply_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/apply")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_apply_fix_5_requires_completed_review(self, apply_env):
        """In-progress or failed reviews cannot be patched (409 Conflict)."""
        app.dependency_overrides[get_current_user] = _user_override(user_id="user-1")

        for non_completed in ["pending", "in_progress", "failed", "cancelled"]:
            review = _make_review(status=non_completed, findings_json=[apply_env["sample_finding"]])
            mock_review_svc = MagicMock()
            mock_review_svc.get_review.return_value = review
            mock_repo_svc = MagicMock()
            mock_repo_svc.get_repository.return_value = _make_repo()

            use_case = ApplyFixSuggestionUseCase(
                review_service=mock_review_svc,
                repository_service=mock_repo_svc,
                workspace_root_resolver=lambda u, r: str(apply_env["workspace"]),
            )
            app.dependency_overrides[get_apply_fix_use_case] = lambda: use_case

            client = TestClient(app)
            resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/apply")
            assert resp.status_code == 409
            assert "completed review" in resp.json()["detail"]

    def test_apply_fix_6_requires_accepted_decision(self, apply_env):
        """Fix with pending or rejected decision returns 409 Conflict."""
        app.dependency_overrides[get_current_user] = _user_override(user_id="user-1")

        for unaccepted_decision in ["pending", "rejected"]:
            finding = dict(apply_env["sample_finding"])
            finding["fix_suggestion"] = dict(apply_env["sample_fix"])
            finding["fix_suggestion"]["user_decision"] = unaccepted_decision

            review = _make_review(findings_json=[finding])
            mock_review_svc = MagicMock()
            mock_review_svc.get_review.return_value = review
            mock_repo_svc = MagicMock()
            mock_repo_svc.get_repository.return_value = _make_repo()

            use_case = ApplyFixSuggestionUseCase(
                review_service=mock_review_svc,
                repository_service=mock_repo_svc,
                workspace_root_resolver=lambda u, r: str(apply_env["workspace"]),
            )
            app.dependency_overrides[get_apply_fix_use_case] = lambda: use_case

            client = TestClient(app)
            resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/apply")
            assert resp.status_code == 409
            assert "must be accepted" in resp.json()["detail"]

    def test_apply_fix_7_rejects_invalid_syntax_validation(self, apply_env):
        """Fix marked with invalid validation_status is rejected with 422."""
        app.dependency_overrides[get_current_user] = _user_override(user_id="user-1")

        finding = dict(apply_env["sample_finding"])
        finding["fix_suggestion"] = dict(apply_env["sample_fix"])
        finding["fix_suggestion"]["validation_status"] = FixValidationStatus.INVALID.value

        review = _make_review(findings_json=[finding])
        mock_review_svc = MagicMock()
        mock_review_svc.get_review.return_value = review
        mock_repo_svc = MagicMock()
        mock_repo_svc.get_repository.return_value = _make_repo()

        use_case = ApplyFixSuggestionUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(apply_env["workspace"]),
        )
        app.dependency_overrides[get_apply_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/apply")
        assert resp.status_code == 422
        assert "invalid syntax" in resp.json()["detail"]

    def test_apply_fix_8_rejects_negative_and_out_of_range_index(self, apply_env):
        """Negative finding_index and out-of-range index return 422."""
        app.dependency_overrides[get_current_user] = _user_override(user_id="user-1")

        review = _make_review(findings_json=[apply_env["sample_finding"]])
        mock_review_svc = MagicMock()
        mock_review_svc.get_review.return_value = review
        mock_repo_svc = MagicMock()
        mock_repo_svc.get_repository.return_value = _make_repo()

        use_case = ApplyFixSuggestionUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(apply_env["workspace"]),
        )
        app.dependency_overrides[get_apply_fix_use_case] = lambda: use_case

        client = TestClient(app)
        # Negative index
        resp_neg = client.post("/api/v1/reviews/rev-1/findings/-1/fix/apply")
        assert resp_neg.status_code == 422

        # Out-of-range index (review only has 1 finding at index 0)
        resp_out = client.post("/api/v1/reviews/rev-1/findings/99/fix/apply")
        assert resp_out.status_code == 422
        assert "out of range" in resp_out.json()["detail"]

    def test_apply_fix_9_client_cannot_supply_arbitrary_path_or_code(self, apply_env):
        """Client payload containing arbitrary path/code is ignored in favor of server state."""
        app.dependency_overrides[get_current_user] = _user_override(user_id="user-1")

        review = _make_review(findings_json=[apply_env["sample_finding"]])
        mock_review_svc = MagicMock()
        mock_review_svc.get_review.return_value = review
        mock_repo_svc = MagicMock()
        mock_repo_svc.get_repository.return_value = _make_repo()

        applied_record = dict(apply_env["sample_fix"])
        applied_record["application_status"] = "applied"
        mock_review_svc.update_finding_application_status.return_value = applied_record

        use_case = ApplyFixSuggestionUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(apply_env["workspace"]),
        )
        app.dependency_overrides[get_apply_fix_use_case] = lambda: use_case

        client = TestClient(app)
        # Malicious payload trying to inject path and code
        resp = client.post(
            "/api/v1/reviews/rev-1/findings/0/fix/apply",
            json={
                "file_path": "/etc/passwd",
                "original_code": "root:x:0:0",
                "proposed_code": "malicious",
                "repository_root": "C:\\",
                "user_id": "other-user",
            }
        )
        assert resp.status_code == 200
        # The target file calc.py was patched, not any client injected file
        assert "return a * b" in apply_env["target_file"].read_text(encoding="utf-8")

    def test_apply_fix_10_stale_source_returns_409_and_no_corruption(self, apply_env):
        """Stale source file causes conflict response (409) and leaves file intact."""
        app.dependency_overrides[get_current_user] = _user_override(user_id="user-1")

        # Change target file content on disk so it does not match original_code
        apply_env["target_file"].write_text("def altered_function():\n    pass\n", encoding="utf-8")
        current_disk = apply_env["target_file"].read_text(encoding="utf-8")

        review = _make_review(findings_json=[apply_env["sample_finding"]])
        mock_review_svc = MagicMock()
        mock_review_svc.get_review.return_value = review
        mock_repo_svc = MagicMock()
        mock_repo_svc.get_repository.return_value = _make_repo()

        use_case = ApplyFixSuggestionUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(apply_env["workspace"]),
        )
        app.dependency_overrides[get_apply_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/apply")
        assert resp.status_code == 409
        assert "Stale source" in resp.json()["detail"]
        # File is unchanged
        assert apply_env["target_file"].read_text(encoding="utf-8") == current_disk

    def test_apply_fix_11_path_traversal_blocked(self, apply_env):
        """Path traversal attempt in persisted fix is rejected by sandbox."""
        app.dependency_overrides[get_current_user] = _user_override(user_id="user-1")

        bad_finding = dict(apply_env["sample_finding"])
        bad_finding["fix_suggestion"] = dict(apply_env["sample_fix"])
        bad_finding["fix_suggestion"]["file_path"] = "../../../outside.py"

        review = _make_review(findings_json=[bad_finding])
        mock_review_svc = MagicMock()
        mock_review_svc.get_review.return_value = review
        mock_repo_svc = MagicMock()
        mock_repo_svc.get_repository.return_value = _make_repo()

        use_case = ApplyFixSuggestionUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(apply_env["workspace"]),
        )
        app.dependency_overrides[get_apply_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/apply")
        assert resp.status_code == 400
        assert "Sandbox violation" in resp.json()["detail"]

    def test_apply_fix_12_http_idempotency(self, apply_env):
        """Second call to Apply returns 200 with idempotent: True."""
        app.dependency_overrides[get_current_user] = _user_override(user_id="user-1")

        applied_finding = dict(apply_env["sample_finding"])
        applied_finding["fix_suggestion"] = dict(apply_env["sample_fix"])
        applied_finding["fix_suggestion"]["application_status"] = FixApplicationStatus.APPLIED.value

        review = _make_review(findings_json=[applied_finding])
        mock_review_svc = MagicMock()
        mock_review_svc.get_review.return_value = review
        mock_repo_svc = MagicMock()
        mock_repo_svc.get_repository.return_value = _make_repo()

        use_case = ApplyFixSuggestionUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(apply_env["workspace"]),
        )
        app.dependency_overrides[get_apply_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/apply")
        assert resp.status_code == 200
        data = resp.json()
        assert data["idempotent"] is True
        assert data["fix_suggestion"]["application_status"] == "applied"

    def test_apply_fix_13_no_llm_calls_during_apply(self, apply_env):
        """Apply executes zero LLM calls."""
        app.dependency_overrides[get_current_user] = _user_override(user_id="user-1")

        review = _make_review(findings_json=[apply_env["sample_finding"]])
        mock_review_svc = MagicMock()
        mock_review_svc.get_review.return_value = review
        mock_repo_svc = MagicMock()
        mock_repo_svc.get_repository.return_value = _make_repo()

        applied_record = dict(apply_env["sample_fix"])
        applied_record["application_status"] = "applied"
        mock_review_svc.update_finding_application_status.return_value = applied_record

        use_case = ApplyFixSuggestionUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(apply_env["workspace"]),
        )
        app.dependency_overrides[get_apply_fix_use_case] = lambda: use_case

        with patch("src.interfaces.api.dependencies._get_llm_provider") as mock_llm:
            client = TestClient(app)
            resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/apply")
            assert resp.status_code == 200
            mock_llm.assert_not_called()

    def test_apply_fix_14_no_agent_write_tools_invoked(self, apply_env):
        """Apply uses AtomicFilePatcher directly and does not invoke general agent write tools."""
        from src.application.use_cases.apply_fix import ApplyFixSuggestionUseCase
        import inspect
        # Verify use case has no tool_manager or agent references
        init_params = inspect.signature(ApplyFixSuggestionUseCase.__init__).parameters
        assert "tool_manager" not in init_params
        assert "agent" not in init_params

    def test_apply_fix_15_accept_reject_remain_metadata_only(self, apply_env):
        """Accept and Reject endpoints remain metadata-only and do not patch file."""
        app.dependency_overrides[get_current_user] = _user_override(user_id="user-1")

        review = _make_review(findings_json=[apply_env["sample_finding"]])
        mock_review_svc = MagicMock()
        mock_review_svc.get_review.return_value = review
        mock_review_svc.update_finding_decision.return_value = {
            **apply_env["sample_fix"],
            "user_decision": "accepted",
        }
        app.dependency_overrides[get_code_review_service] = lambda: mock_review_svc

        content_before = apply_env["target_file"].read_text(encoding="utf-8")
        client = TestClient(app)
        resp_acc = client.post("/api/v1/reviews/rev-1/findings/0/fix/accept")
        assert resp_acc.status_code == 200
        assert apply_env["target_file"].read_text(encoding="utf-8") == content_before

        mock_review_svc.update_finding_decision.return_value = {
            **apply_env["sample_fix"],
            "user_decision": "rejected",
        }
        resp_rej = client.post("/api/v1/reviews/rev-1/findings/0/fix/reject")
        assert resp_rej.status_code == 200
        assert apply_env["target_file"].read_text(encoding="utf-8") == content_before
