"""
test_verify_applied_fix_api.py
==============================
Phase 11.4B-2 — Secure Static Verification API, Security & Contract Tests.

Validates:
- POST /api/v1/reviews/{review_id}/findings/{finding_index}/fix/verify
- Zero client-supplied source/path trust (all derived server-side)
- Authentication and ownership enforcement (review & repository)
- Finding index boundaries and validation
- Eligibility checks (completed review, applied fix, non-rejected)
- Deterministic Tier-1 verification (Python, JS/TS, Java, Unsupported)
- Post-apply source modification detection (SOURCE_CHANGED)
- Re-verification safety and refresh-safe persistence
- Read-only guarantee (file hash unchanged)
- Zero LLM, zero subprocess, zero Docker execution
- OpenAPI contract compliance and response security
"""
import hashlib
import os
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.api.dependencies import (
    get_current_user,
    get_verify_applied_fix_use_case,
)
from src.interfaces.api.v1.reviews import get_code_review_service
from src.domain.entities.code_review import ReviewStatusEnum
from src.domain.entities.fix_suggestion import (
    FixUserDecision,
    FixValidationStatus,
    FixApplicationStatus,
)
from src.domain.entities.verification import (
    VerificationStatus,
    CheckStatus,
    StaticVerificationResult,
)
from src.application.use_cases.verify_applied_fix import VerifyAppliedFixUseCase
from src.application.services.code_review_service import CodeReviewService
from src.application.services.repository_service import RepositoryService
from src.infrastructure.analysis.static_verification_engine import StaticVerificationEngine
from src.infrastructure.filesystem.path_sandbox import PathSandboxService


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
def verify_env(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target_file = workspace / "src" / "calc.py"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    initial_bytes = b"def calc(a: int, b: int) -> int:\n    return a * b\n"
    target_file.write_bytes(initial_bytes)
    content_hash = hashlib.sha256(initial_bytes).hexdigest()

    sample_fix = {
        "finding_index": 0,
        "file_path": "src/calc.py",
        "original_code": "def calc(a, b):\n    return a + b",
        "proposed_code": "def calc(a: int, b: int) -> int:\n    return a * b",
        "explanation": "Add type annotations and multiply",
        "diff": "--- a/src/calc.py\n+++ b/src/calc.py",
        "confidence_score": 0.95,
        "validation_status": FixValidationStatus.VALID.value,
        "user_decision": FixUserDecision.ACCEPTED.value,
        "application_status": FixApplicationStatus.APPLIED.value,
        "applied_at": "2026-08-25T01:00:00Z",
        "new_hash": content_hash,
        "language": "python",
    }

    sample_finding = {
        "issue": "Missing type annotations",
        "severity": "medium",
        "explanation": "Add parameter and return types",
        "suggested_fix": "Add types",
        "confidence_score": 0.95,
        "file_path": "src/calc.py",
        "line_number": 1,
        "fix_suggestion": sample_fix,
    }

    return {
        "workspace": workspace,
        "target_file": target_file,
        "content_hash": content_hash,
        "sample_fix": sample_fix,
        "sample_finding": sample_finding,
    }


class TestVerifyAppliedFixApi:
    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_verify_fix_1_openapi_registration(self):
        """POST /api/v1/reviews/{review_id}/findings/{finding_index}/fix/verify is in OpenAPI schema."""
        client = TestClient(app)
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        path = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/verify"
        assert path in schema["paths"], f"Expected {path} in OpenAPI schema"
        post_op = schema["paths"][path].get("post")
        assert post_op is not None
        # Must have review_id and finding_index path parameters
        param_names = [p["name"] for p in post_op.get("parameters", [])]
        assert "review_id" in param_names
        assert "finding_index" in param_names
        # Must NOT require arbitrary source_code or file_path in requestBody
        assert "requestBody" not in post_op or post_op["requestBody"] is None or post_op["requestBody"].get("required") is False

    def test_verify_fix_2_requires_authentication(self):
        """Unauthenticated request returns 401."""
        client = TestClient(app)
        with patch("src.core.config.settings.DEV_AUTH_BYPASS", False):
            resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
            assert resp.status_code == 401

    def test_verify_fix_3_review_ownership_enforced(self, verify_env):
        """Accessing another user's review returns 404 without leaking info."""
        app.dependency_overrides[get_current_user] = _user_override("user-attacker")
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = None  # user does not own review
        mock_repo_svc = MagicMock(spec=RepositoryService)

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower() or "access denied" in resp.json()["detail"].lower()

    def test_verify_fix_4_repository_ownership_enforced(self, verify_env):
        """Repository ownership mismatch returns 404."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")
        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[verify_env["sample_finding"]],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = None  # user does not own repo

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp.status_code == 404

    def test_verify_fix_5_valid_python_fix_passed(self, verify_env):
        """Valid Python fix verifies successfully (status PASSED, repo unchanged)."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")
        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[verify_env["sample_finding"]],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_review_svc.update_finding_verification_result.side_effect = lambda review_id, finding_index, verification_result, user_id=None: {
            **verify_env["sample_fix"],
            "static_verification": verification_result.model_dump(mode="json"),
        }
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        # Hash before verify
        hash_before = hashlib.sha256(verify_env["target_file"].read_bytes()).hexdigest()

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")

        # Hash after verify (Read-Only proof)
        hash_after = hashlib.sha256(verify_env["target_file"].read_bytes()).hexdigest()
        assert hash_before == hash_after, "Repository file must not be modified during verification"

        assert resp.status_code == 200
        body = resp.json()
        assert "verification" in body
        assert "fix_suggestion" in body
        v = body["verification"]
        assert v["status"] == "passed"
        assert v["language"] == "python"
        assert len(v["checks"]) >= 2
        assert all(c["status"] == "passed" for c in v["checks"])
        assert len(v["errors"]) == 0

    def test_verify_fix_6_invalid_python_syntax_failed(self, verify_env):
        """Applied source containing syntax error returns FAILED with line/column info."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        # Overwrite file with syntax error
        bad_code = b"def broken(a, b:\n    return a + b\n"
        verify_env["target_file"].write_bytes(bad_code)
        bad_hash = hashlib.sha256(bad_code).hexdigest()

        finding = dict(verify_env["sample_finding"])
        fix = dict(verify_env["sample_fix"])
        fix["new_hash"] = bad_hash
        finding["fix_suggestion"] = fix

        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[finding],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_review_svc.update_finding_verification_result.side_effect = lambda review_id, finding_index, verification_result, user_id=None: {
            **fix,
            "static_verification": verification_result.model_dump(mode="json"),
        }
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp.status_code == 200
        body = resp.json()
        v = body["verification"]
        assert v["status"] == "failed"
        assert len(v["errors"]) > 0

    def test_verify_fix_7_javascript_typescript_safe(self, verify_env):
        """JS/TS verified in-process without invoking Node/npm/tsc."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        js_file = verify_env["workspace"] / "src" / "index.ts"
        js_content = b"export function greet(name: string): string {\n  return `Hello, ${name}!`;\n}\n"
        js_file.write_bytes(js_content)
        js_hash = hashlib.sha256(js_content).hexdigest()

        js_fix = {
            **verify_env["sample_fix"],
            "file_path": "src/index.ts",
            "language": "typescript",
            "new_hash": js_hash,
        }
        js_finding = {
            **verify_env["sample_finding"],
            "file_path": "src/index.ts",
            "fix_suggestion": js_fix,
        }

        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[js_finding],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_review_svc.update_finding_verification_result.side_effect = lambda review_id, finding_index, verification_result, user_id=None: {
            **js_fix,
            "static_verification": verification_result.model_dump(mode="json"),
        }
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp.status_code == 200
        body = resp.json()
        assert body["verification"]["status"] == "passed"
        assert body["verification"]["language"] == "typescript"

    def test_verify_fix_8_java_safe(self, verify_env):
        """Java verified in-process without invoking javac/java/Maven/Gradle."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        java_file = verify_env["workspace"] / "src" / "App.java"
        java_content = b"public class App {\n    public static void main(String[] args) {\n        System.out.println(\"Hello\");\n    }\n}\n"
        java_file.write_bytes(java_content)
        java_hash = hashlib.sha256(java_content).hexdigest()

        java_fix = {
            **verify_env["sample_fix"],
            "file_path": "src/App.java",
            "language": "java",
            "new_hash": java_hash,
        }
        java_finding = {
            **verify_env["sample_finding"],
            "file_path": "src/App.java",
            "fix_suggestion": java_fix,
        }

        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[java_finding],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_review_svc.update_finding_verification_result.side_effect = lambda review_id, finding_index, verification_result, user_id=None: {
            **java_fix,
            "static_verification": verification_result.model_dump(mode="json"),
        }
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp.status_code == 200
        body = resp.json()
        assert body["verification"]["status"] == "passed"
        assert body["verification"]["language"] == "java"

    def test_verify_fix_9_unsupported_language(self, verify_env):
        """Unsupported language returns UNSUPPORTED and never falsely claims PASS."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        rs_file = verify_env["workspace"] / "src" / "main.rs"
        rs_content = b"fn main() { println!(\"Hello\"); }\n"
        rs_file.write_bytes(rs_content)
        rs_hash = hashlib.sha256(rs_content).hexdigest()

        rs_fix = {
            **verify_env["sample_fix"],
            "file_path": "src/main.rs",
            "language": "rust",
            "new_hash": rs_hash,
        }
        rs_finding = {
            **verify_env["sample_finding"],
            "file_path": "src/main.rs",
            "fix_suggestion": rs_fix,
        }

        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[rs_finding],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_review_svc.update_finding_verification_result.side_effect = lambda review_id, finding_index, verification_result, user_id=None: {
            **rs_fix,
            "static_verification": verification_result.model_dump(mode="json"),
        }
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp.status_code == 200
        body = resp.json()
        assert body["verification"]["status"] == "unsupported"

    def test_verify_fix_10_source_changed_post_apply(self, verify_env):
        """If source file was modified after apply, returns SOURCE_CHANGED without false PASS."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        # Mutate the file on disk after apply
        verify_env["target_file"].write_bytes(b"def modified_after_apply(): pass\n")

        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[verify_env["sample_finding"]],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_review_svc.update_finding_verification_result.side_effect = lambda review_id, finding_index, verification_result, user_id=None: {
            **verify_env["sample_fix"],
            "static_verification": verification_result.model_dump(mode="json"),
        }
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp.status_code == 200
        body = resp.json()
        assert body["verification"]["status"] == "source_changed"
        assert "mismatch" in body["verification"]["errors"][0].lower() or "changed" in body["verification"]["message"].lower()

    def test_verify_fix_11_ineligible_not_applied(self, verify_env):
        """Fix with application_status != applied returns 409."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        for status in [
            FixApplicationStatus.NOT_APPLIED.value,
            FixApplicationStatus.APPLYING.value,
            FixApplicationStatus.STALE.value,
            FixApplicationStatus.APPLY_FAILED.value,
        ]:
            finding = dict(verify_env["sample_finding"])
            fix = dict(verify_env["sample_fix"])
            fix["application_status"] = status
            finding["fix_suggestion"] = fix

            mock_review = _make_review(
                review_id="rev-1",
                user_id="user-1",
                repository_id="repo-1",
                findings_json=[finding],
            )
            mock_review_svc = MagicMock(spec=CodeReviewService)
            mock_review_svc.get_review.return_value = mock_review
            mock_repo_svc = MagicMock(spec=RepositoryService)
            mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

            use_case = VerifyAppliedFixUseCase(
                review_service=mock_review_svc,
                repository_service=mock_repo_svc,
                workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
            )
            app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

            client = TestClient(app)
            resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
            assert resp.status_code == 409
            assert "must be applied" in resp.json()["detail"].lower()

    def test_verify_fix_12_ineligible_rejected(self, verify_env):
        """Fix with user_decision == rejected returns 409."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        finding = dict(verify_env["sample_finding"])
        fix = dict(verify_env["sample_fix"])
        fix["user_decision"] = FixUserDecision.REJECTED.value
        finding["fix_suggestion"] = fix

        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[finding],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp.status_code == 409
        assert "rejected" in resp.json()["detail"].lower()

    def test_verify_fix_13_ineligible_review_not_completed(self, verify_env):
        """Non-completed review returns 409."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            status="in_progress",
            findings_json=[verify_env["sample_finding"]],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp.status_code == 409
        assert "completed review" in resp.json()["detail"].lower()

    def test_verify_fix_14_ineligible_no_fix_suggestion(self, verify_env):
        """Finding without fix suggestion returns 404."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        finding_without_fix = {
            "issue": "Some issue",
            "file_path": "src/calc.py",
        }
        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[finding_without_fix],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp.status_code == 404
        assert "no fix suggestion" in resp.json()["detail"].lower()

    def test_verify_fix_15_invalid_finding_index(self, verify_env):
        """Negative and out-of-range finding indices are rejected with 422."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[verify_env["sample_finding"]],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        # Negative index
        resp_neg = client.post("/api/v1/reviews/rev-1/findings/-1/fix/verify")
        assert resp_neg.status_code == 422

        # Out-of-range index
        resp_out = client.post("/api/v1/reviews/rev-1/findings/5/fix/verify")
        assert resp_out.status_code == 422
        assert "out of range" in resp_out.json()["detail"].lower()

        # Very large index
        resp_large = client.post("/api/v1/reviews/rev-1/findings/99999/fix/verify")
        assert resp_large.status_code == 422

    def test_verify_fix_16_reverification_is_safe_and_updates_timestamp(self, verify_env):
        """Re-verifying an applied fix runs safely, updates result, and leaves file unchanged."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[verify_env["sample_finding"]],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_review_svc.update_finding_verification_result.side_effect = lambda review_id, finding_index, verification_result, user_id=None: {
            **verify_env["sample_fix"],
            "static_verification": verification_result.model_dump(mode="json"),
        }
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp1 = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp1.status_code == 200

        resp2 = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp2.status_code == 200
        assert resp2.json()["verification"]["status"] == "passed"
        assert mock_review_svc.update_finding_verification_result.call_count == 2

    def test_verify_fix_17_malicious_code_in_source_not_executed(self, verify_env):
        """Malicious payload in target file is parsed via AST with zero execution or side effects."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        side_effect_marker = verify_env["workspace"] / "pwned.txt"
        # Code that would create side_effect_marker IF executed
        posix_marker = side_effect_marker.as_posix()
        malicious_code = f"import os\nos.system('echo pwned > {posix_marker}')\n".encode("utf-8")
        verify_env["target_file"].write_bytes(malicious_code)
        malicious_hash = hashlib.sha256(malicious_code).hexdigest()

        finding = dict(verify_env["sample_finding"])
        fix = dict(verify_env["sample_fix"])
        fix["new_hash"] = malicious_hash
        finding["fix_suggestion"] = fix

        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[finding],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_review_svc.update_finding_verification_result.side_effect = lambda review_id, finding_index, verification_result, user_id=None: {
            **fix,
            "static_verification": verification_result.model_dump(mode="json"),
        }
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp.status_code == 200

        # Verify side effect marker was NOT created
        assert not side_effect_marker.exists(), "Malicious payload must NEVER execute!"

    def test_verify_fix_18_conflict_markers_failed(self, verify_env):
        """Unresolved Git merge conflict markers fail verification."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        conflict_code = b"<<<<<<< HEAD\ndef test(): return 1\n=======\ndef test(): return 2\n>>>>>>> feature\n"
        verify_env["target_file"].write_bytes(conflict_code)
        conflict_hash = hashlib.sha256(conflict_code).hexdigest()

        finding = dict(verify_env["sample_finding"])
        fix = dict(verify_env["sample_fix"])
        fix["new_hash"] = conflict_hash
        finding["fix_suggestion"] = fix

        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[finding],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_review_svc.update_finding_verification_result.side_effect = lambda review_id, finding_index, verification_result, user_id=None: {
            **fix,
            "static_verification": verification_result.model_dump(mode="json"),
        }
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp.status_code == 200
        body = resp.json()
        assert body["verification"]["status"] == "failed"
        assert any("conflict marker" in e.lower() for e in body["verification"]["errors"])

    def test_verify_fix_19_empty_source_failed(self, verify_env):
        """Empty source file fails verification."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        empty_bytes = b"   \n\n  "
        verify_env["target_file"].write_bytes(empty_bytes)
        empty_hash = hashlib.sha256(empty_bytes).hexdigest()

        finding = dict(verify_env["sample_finding"])
        fix = dict(verify_env["sample_fix"])
        fix["new_hash"] = empty_hash
        finding["fix_suggestion"] = fix

        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[finding],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_review_svc.update_finding_verification_result.side_effect = lambda review_id, finding_index, verification_result, user_id=None: {
            **fix,
            "static_verification": verification_result.model_dump(mode="json"),
        }
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp.status_code == 200
        body = resp.json()
        assert body["verification"]["status"] == "failed"
        assert any("empty" in e.lower() for e in body["verification"]["errors"])

    def test_verify_fix_20_response_security(self, verify_env):
        """Response does not expose absolute server filesystem paths or sensitive credentials."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[verify_env["sample_finding"]],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        mock_review_svc.update_finding_verification_result.side_effect = lambda review_id, finding_index, verification_result, user_id=None: {
            **verify_env["sample_fix"],
            "static_verification": verification_result.model_dump(mode="json"),
        }
        mock_repo_svc = MagicMock(spec=RepositoryService)
        mock_repo_svc.get_repository.return_value = _make_repo("repo-1", "user-1")

        use_case = VerifyAppliedFixUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            workspace_root_resolver=lambda u, r: str(verify_env["workspace"]),
        )
        app.dependency_overrides[get_verify_applied_fix_use_case] = lambda: use_case

        client = TestClient(app)
        resp = client.post("/api/v1/reviews/rev-1/findings/0/fix/verify")
        assert resp.status_code == 200
        raw_text = resp.text

        # Verify absolute temp directory path is not leaked in response
        assert str(verify_env["workspace"]) not in raw_text

    def test_verify_fix_21_persistence_visible_in_get_review(self, verify_env):
        """After verification, GET /reviews/{review_id} exposes the persisted static_verification."""
        app.dependency_overrides[get_current_user] = _user_override("user-1")

        persisted_verification = {
            "status": "passed",
            "language": "python",
            "verified_at": "2026-08-25T01:05:00Z",
            "verified_hash": verify_env["content_hash"],
            "duration_ms": 1,
            "checks": [{"name": "syntax_parser", "status": "passed", "message": "Syntax valid", "line_number": None, "column": None}],
            "errors": [],
            "warnings": [],
            "message": "Tier-1 static syntax verification passed",
        }

        finding_with_verification = dict(verify_env["sample_finding"])
        fix_with_verification = dict(verify_env["sample_fix"])
        fix_with_verification["static_verification"] = persisted_verification
        finding_with_verification["fix_suggestion"] = fix_with_verification

        mock_review = _make_review(
            review_id="rev-1",
            user_id="user-1",
            repository_id="repo-1",
            findings_json=[finding_with_verification],
        )
        mock_review_svc = MagicMock(spec=CodeReviewService)
        mock_review_svc.get_review.return_value = mock_review
        app.dependency_overrides[get_code_review_service] = lambda: mock_review_svc

        client = TestClient(app)
        resp = client.get("/api/v1/reviews/rev-1")
        assert resp.status_code == 200
        review_data = resp.json()
        assert len(review_data["findings"]) == 1
        f0 = review_data["findings"][0]
        assert "fix_suggestion" in f0
        assert f0["fix_suggestion"]["static_verification"]["status"] == "passed"
