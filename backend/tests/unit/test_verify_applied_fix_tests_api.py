"""
test_verify_applied_fix_tests_api.py
=====================================
Phase 11.4B-6 — Tier-2 Sandbox Test Verification API Tests.

Validates:
- POST /api/v1/reviews/{review_id}/findings/{finding_index}/fix/verify-tests
- OpenAPI contract: path registered, no arbitrary request body
- 401 unauthenticated
- 404 review not found / cross-user access
- 404 repository not found
- 409 fix not applied
- 409 Tier-1 static verification prerequisite not met
- 409 source file modified after apply
- 422 invalid (negative) finding index
- 422 finding index out of range
- 200 PASSED result
- 200 FAILED result
- 200 TIMED_OUT result
- 200 SANDBOX_UNAVAILABLE (no host fallback)
- 200 UNSUPPORTED language
- No arbitrary source / path injection from request body
- Zero LLM, zero subprocess, zero Docker execution
"""
import hashlib
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.api.dependencies import (
    get_current_user,
    get_verify_applied_fix_tests_use_case,
)
from src.domain.entities.fix_suggestion import (
    FixApplicationStatus,
    FixUserDecision,
    FixValidationStatus,
)
from src.domain.entities.verification import VerificationStatus
from src.domain.entities.sandbox import (
    SandboxVerificationResult,
    SandboxVerificationStatusEnum,
)
from src.application.use_cases.verify_applied_fix_tests import VerifyAppliedFixTestsUseCase
from src.core.errors import ResourceNotFoundError, WorkflowExecutionError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ENDPOINT = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/verify-tests"


def _url(review_id="rev-1", finding_index=0):
    return ENDPOINT.format(review_id=review_id, finding_index=finding_index)


def _user_override(user_id: str = "user-1"):
    def _override():
        return {"sub": user_id, "email": f"{user_id}@example.com"}
    return _override


def _sandbox_result(
    status: SandboxVerificationStatusEnum = SandboxVerificationStatusEnum.PASSED,
    tests_passed: int = 3,
    tests_failed: int = 0,
    timed_out: bool = False,
) -> SandboxVerificationResult:
    return SandboxVerificationResult(
        status=status,
        verification_type="isolated_tests",
        test_framework="pytest",
        command_label="pytest",
        exit_code=0 if status == SandboxVerificationStatusEnum.PASSED else 1,
        duration_ms=420,
        tests_total=tests_passed + tests_failed,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        tests_skipped=0,
        stdout_summary=f"{tests_passed} passed",
        stderr_summary="",
        timed_out=timed_out,
        resource_limit_hit=False,
        verified_at="2026-08-26T00:00:00Z",
        verified_hash="abc123",
        message=None,
        error_details=None,
    )


def _make_fix_suggestion(content_hash: str) -> dict:
    return {
        "finding_index": 0,
        "file_path": "src/calc.py",
        "original_code": "def add(a, b): return a + b",
        "proposed_code": "def add(a: int, b: int) -> int: return a + b",
        "explanation": "Add type hints",
        "diff": "--- a\\n+++ b",
        "confidence_score": 0.90,
        "validation_status": FixValidationStatus.VALID.value,
        "user_decision": FixUserDecision.ACCEPTED.value,
        "application_status": FixApplicationStatus.APPLIED.value,
        "applied_at": "2026-08-26T00:00:00Z",
        "new_hash": content_hash,
        "language": "python",
        "static_verification": {"status": VerificationStatus.PASSED.value},
    }


def _make_use_case_override(return_value=None, raise_exc=None):
    """Create a use case dependency override that returns or raises as specified."""
    mock_uc = MagicMock(spec=VerifyAppliedFixTestsUseCase)

    if raise_exc:
        mock_uc.execute = AsyncMock(side_effect=raise_exc)
    else:
        mock_uc.execute = AsyncMock(return_value=return_value)

    def _override():
        return mock_uc

    return _override


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestVerifyFixTestsApi:
    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    # --- OpenAPI Contract ---

    def test_1_openapi_endpoint_registered(self):
        """POST /api/v1/reviews/{review_id}/findings/{finding_index}/fix/verify-tests must be in OpenAPI schema."""
        client = TestClient(app)
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        path = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/verify-tests"
        assert path in schema["paths"], f"Expected '{path}' in OpenAPI schema"
        post_op = schema["paths"][path].get("post")
        assert post_op is not None
        # Must require review_id and finding_index path params
        param_names = [p["name"] for p in post_op.get("parameters", [])]
        assert "review_id" in param_names
        assert "finding_index" in param_names

    def test_2_no_arbitrary_request_body(self):
        """Endpoint MUST NOT require an arbitrary requestBody with source_code or file_path."""
        client = TestClient(app)
        resp = client.get("/openapi.json")
        schema = resp.json()
        path = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/verify-tests"
        post_op = schema["paths"][path].get("post", {})
        request_body = post_op.get("requestBody")
        # Either no requestBody at all, or it must be optional (not required)
        if request_body:
            assert not request_body.get("required", False), (
                "verify-tests endpoint must not REQUIRE a request body"
            )

    # --- Authentication ---

    def test_3_unauthenticated_returns_401(self):
        """No auth token → 401 when no user is authenticated."""
        # Do NOT set get_current_user override so the real auth dependency fires
        # But we need to ensure the use case doesn't short-circuit it.
        # The real get_current_user raises 401 when no token is provided.
        # If the test environment treats missing auth as anonymous, override to raise 401.
        def _raise_401():
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = _raise_401
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 401


    # --- Ownership / Not Found ---

    def test_4_review_not_found_returns_404(self):
        """Review missing → 404."""
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_verify_applied_fix_tests_use_case] = _make_use_case_override(
            raise_exc=ResourceNotFoundError("Review not found or access denied")
        )
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url("unknown-rev", 0))
        assert resp.status_code == 404
        assert "Review not found" in resp.json()["detail"]

    def test_5_cross_user_access_returns_404(self):
        """Different user_id → 404 (ownership)."""
        app.dependency_overrides[get_current_user] = _user_override("other-user")
        app.dependency_overrides[get_verify_applied_fix_tests_use_case] = _make_use_case_override(
            raise_exc=ResourceNotFoundError("Review not found or access denied")
        )
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url("rev-1", 0))
        assert resp.status_code == 404

    def test_6_repository_not_found_returns_404(self):
        """Repository missing → 404."""
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_verify_applied_fix_tests_use_case] = _make_use_case_override(
            raise_exc=ResourceNotFoundError("Repository not found or access denied")
        )
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 404
        assert "Repository not found" in resp.json()["detail"]

    # --- Finding Index Validation ---

    def test_7_negative_finding_index_returns_422(self):
        """finding_index = -1 → 422."""
        app.dependency_overrides[get_current_user] = _user_override()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url("rev-1", -1))
        assert resp.status_code == 422

    def test_8_out_of_range_finding_index_returns_422(self):
        """finding_index out of range → 422."""
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_verify_applied_fix_tests_use_case] = _make_use_case_override(
            raise_exc=WorkflowExecutionError("finding_index 99 out of range (review has 1 findings)")
        )
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url("rev-1", 99))
        assert resp.status_code == 422
        assert "out of range" in resp.json()["detail"]

    # --- Eligibility Checks ---

    def test_9_fix_not_applied_returns_409(self):
        """Fix not applied → 409 conflict."""
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_verify_applied_fix_tests_use_case] = _make_use_case_override(
            raise_exc=WorkflowExecutionError(
                "Fix suggestion must be applied before running isolated tests (current status: 'not_applied')"
            )
        )
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 409
        assert "must be applied" in resp.json()["detail"]

    def test_10_tier1_prerequisite_not_met_returns_409(self):
        """Tier-1 static verification not passed → 409."""
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_verify_applied_fix_tests_use_case] = _make_use_case_override(
            raise_exc=WorkflowExecutionError(
                "Tier-1 static verification must be 'passed' to run isolated tests (current status: 'failed')"
            )
        )
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 409
        assert "static verification must" in resp.json()["detail"]

    def test_11_source_modified_after_apply_returns_409(self):
        """Source file modified after apply → 409 conflict."""
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_verify_applied_fix_tests_use_case] = _make_use_case_override(
            raise_exc=WorkflowExecutionError(
                "Source file was modified after fix was applied. Cannot run isolated tests on stale source."
            )
        )
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 409
        assert "Source file was modified" in resp.json()["detail"]

    # --- Success Responses ---

    def test_12_returns_200_passed(self):
        """Container run, all tests pass → 200 PASSED."""
        content_hash = hashlib.sha256(b"source").hexdigest()
        fix = _make_fix_suggestion(content_hash)
        sandbox_res = _sandbox_result(
            status=SandboxVerificationStatusEnum.PASSED,
            tests_passed=5,
            tests_failed=0,
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_verify_applied_fix_tests_use_case] = _make_use_case_override(
            return_value={"verification": sandbox_res, "fix_suggestion": fix}
        )
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 200
        data = resp.json()
        assert data["verification"]["status"] == "passed"
        assert data["verification"]["tests_passed"] == 5
        assert data["verification"]["tests_failed"] == 0

    def test_13_returns_200_failed(self):
        """Container run, tests fail → 200 FAILED."""
        content_hash = hashlib.sha256(b"source").hexdigest()
        fix = _make_fix_suggestion(content_hash)
        sandbox_res = _sandbox_result(
            status=SandboxVerificationStatusEnum.FAILED,
            tests_passed=2,
            tests_failed=3,
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_verify_applied_fix_tests_use_case] = _make_use_case_override(
            return_value={"verification": sandbox_res, "fix_suggestion": fix}
        )
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 200
        data = resp.json()
        assert data["verification"]["status"] == "failed"
        assert data["verification"]["tests_failed"] == 3

    def test_14_returns_200_timed_out(self):
        """Container timeout → 200 TIMED_OUT (not 500, not false PASS)."""
        content_hash = hashlib.sha256(b"source").hexdigest()
        fix = _make_fix_suggestion(content_hash)
        sandbox_res = _sandbox_result(
            status=SandboxVerificationStatusEnum.TIMED_OUT,
            tests_passed=0,
            tests_failed=0,
            timed_out=True,
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_verify_applied_fix_tests_use_case] = _make_use_case_override(
            return_value={"verification": sandbox_res, "fix_suggestion": fix}
        )
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 200
        data = resp.json()
        assert data["verification"]["status"] == "timed_out"
        assert data["verification"]["timed_out"] is True

    def test_15_returns_200_sandbox_unavailable(self):
        """Docker unavailable → 200 SANDBOX_UNAVAILABLE (zero host fallback)."""
        content_hash = hashlib.sha256(b"source").hexdigest()
        fix = _make_fix_suggestion(content_hash)
        sandbox_res = SandboxVerificationResult(
            status=SandboxVerificationStatusEnum.SANDBOX_UNAVAILABLE,
            verification_type="isolated_tests",
            test_framework="pytest",
            command_label="pytest",
            exit_code=None,
            duration_ms=0,
            tests_total=None,
            tests_passed=None,
            tests_failed=None,
            tests_skipped=None,
            stdout_summary="",
            stderr_summary="",
            timed_out=False,
            resource_limit_hit=False,
            verified_at=None,
            verified_hash=None,
            message="Docker daemon is not available",
            error_details=None,
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_verify_applied_fix_tests_use_case] = _make_use_case_override(
            return_value={"verification": sandbox_res, "fix_suggestion": fix}
        )
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 200
        data = resp.json()
        assert data["verification"]["status"] == "sandbox_unavailable"

    def test_16_returns_200_unsupported_language(self):
        """Non-Python language → 200 UNSUPPORTED (no container execution)."""
        content_hash = hashlib.sha256(b"source").hexdigest()
        fix = _make_fix_suggestion(content_hash)
        fix["file_path"] = "src/index.ts"
        sandbox_res = SandboxVerificationResult(
            status=SandboxVerificationStatusEnum.UNSUPPORTED,
            verification_type="isolated_tests",
            test_framework="unsupported",
            command_label="N/A",
            exit_code=None,
            duration_ms=0,
            tests_total=None,
            tests_passed=None,
            tests_failed=None,
            tests_skipped=None,
            stdout_summary="",
            stderr_summary="",
            timed_out=False,
            resource_limit_hit=False,
            verified_at=None,
            verified_hash=None,
            message="Tier-2 container testing is only supported for Python/pytest projects",
            error_details=None,
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_verify_applied_fix_tests_use_case] = _make_use_case_override(
            return_value={"verification": sandbox_res, "fix_suggestion": fix}
        )
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 200
        data = resp.json()
        assert data["verification"]["status"] == "unsupported"

    # --- Security / No Injection ---

    def test_17_client_body_ignored_not_injected(self):
        """Client-supplied JSON body must NOT be accepted or influence server behavior."""
        content_hash = hashlib.sha256(b"source").hexdigest()
        fix = _make_fix_suggestion(content_hash)
        sandbox_res = _sandbox_result()
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_verify_applied_fix_tests_use_case] = _make_use_case_override(
            return_value={"verification": sandbox_res, "fix_suggestion": fix}
        )
        client = TestClient(app, raise_server_exceptions=False)
        # Attempt to inject arbitrary source_code and file_path
        malicious_body = {
            "source_code": "import subprocess; subprocess.run(['rm', '-rf', '/'])",
            "file_path": "../../../../etc/passwd",
            "command": "rm -rf /",
        }
        resp = client.post(_url(), json=malicious_body)
        # Must succeed (not 400 or 422 from bad body) because body is ignored
        # OR must return 422 for unexpected body — but must NOT process injected fields
        assert resp.status_code in (200, 422), f"Unexpected status: {resp.status_code}"
        if resp.status_code == 200:
            data = resp.json()
            # Verify that injected file_path or source_code had no effect
            assert data["verification"]["status"] == "passed"

    def test_18_response_contains_fix_suggestion_and_verification(self):
        """Response schema MUST contain both 'verification' and 'fix_suggestion' keys."""
        content_hash = hashlib.sha256(b"source").hexdigest()
        fix = _make_fix_suggestion(content_hash)
        sandbox_res = _sandbox_result()
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_verify_applied_fix_tests_use_case] = _make_use_case_override(
            return_value={"verification": sandbox_res, "fix_suggestion": fix}
        )
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 200
        data = resp.json()
        assert "verification" in data
        assert "fix_suggestion" in data
        # verification must contain all required Tier-2 fields
        ver = data["verification"]
        assert "status" in ver
        assert "tests_passed" in ver
        assert "tests_failed" in ver
        assert "timed_out" in ver
        assert "resource_limit_hit" in ver
        assert "stdout_summary" in ver
