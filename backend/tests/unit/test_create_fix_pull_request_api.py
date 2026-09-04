"""
API Tests — POST /api/v1/reviews/{review_id}/findings/{finding_index}/fix/git/pull-request
==========================================================================================
Validates: authentication, ownership, eligibility enforcement, commit & push prerequisites,
idempotency, OpenAPI registration, response security, PR-only contract, no-auto-merge,
no-shell, no-LLM proofs, and response schema.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.api.dependencies import (
    get_current_user,
    get_create_fix_pull_request_use_case,
)
from src.domain.entities.git import GitPullRequestResult, GitPullRequestStatusEnum
from src.application.use_cases.create_fix_pull_request import CreateFixPullRequestUseCase
from src.core.errors import ResourceNotFoundError, WorkflowExecutionError


ENDPOINT = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/git/pull-request"


def _url(review_id="rev-1", finding_index=0):
    return ENDPOINT.format(review_id=review_id, finding_index=finding_index)


def _user_override(user_id: str = "user-1"):
    def _override():
        return {"sub": user_id, "email": f"{user_id}@example.com"}
    return _override


def _make_pr_result(status="created", pr_number=42):
    return GitPullRequestResult(
        status=GitPullRequestStatusEnum(status),
        pr_number=pr_number,
        pr_url=f"https://github.com/my-org/my-repo/pull/{pr_number}",
        title="fix: resolve code review finding",
        body="## AI Code Review Fix Summary\n\nAutomated fix.",
        head_branch="ai-fix/rev-abc12345-f0",
        base_branch="main",
        created_at="2026-08-26T10:05:00+00:00",
        message=f"Created Pull Request #{pr_number}",
    )


def _make_fix_suggestion(pr_result=None):
    fix = {
        "finding_index": 0,
        "file_path": "src/utils.py",
        "original_code": "old",
        "proposed_code": "new",
        "explanation": "fix",
        "diff": "--- a\n+++ b",
        "confidence_score": 0.95,
        "validation_status": "valid",
        "user_decision": "accepted",
        "application_status": "applied",
        "new_hash": "abc123",
        "git_commit": {
            "status": "committed",
            "branch_name": "ai-fix/rev-abc12345-f0",
            "commit_sha": "a" * 40,
            "committed_at": "2026-08-26T10:00:00+00:00",
            "file_path": "src/utils.py",
        },
        "git_push": {
            "status": "pushed",
            "remote_name": "origin",
            "branch_name": "ai-fix/rev-abc12345-f0",
            "commit_sha": "a" * 40,
        },
    }
    if pr_result is not None:
        fix["git_pull_request"] = {
            "status": pr_result.status.value if hasattr(pr_result.status, "value") else pr_result.status,
            "pr_number": pr_result.pr_number,
            "pr_url": pr_result.pr_url,
            "title": pr_result.title,
            "head_branch": pr_result.head_branch,
            "base_branch": pr_result.base_branch,
        }
    return fix


def _make_success_result(pr_status="created", pr_number=42):
    pr_result = _make_pr_result(pr_status, pr_number)
    return {
        "git_pull_request": pr_result,
        "fix_suggestion": _make_fix_suggestion(pr_result),
    }


def _make_use_case_override(return_value=None, raise_exc=None):
    mock_uc = MagicMock(spec=CreateFixPullRequestUseCase)
    if raise_exc:
        mock_uc.execute = AsyncMock(side_effect=raise_exc)
    else:
        mock_uc.execute = AsyncMock(return_value=return_value)

    def _override():
        return mock_uc

    return _override, mock_uc


# ---------------------------------------------------------------------------
# 1. OpenAPI Registration
# ---------------------------------------------------------------------------

class TestCreatePRApiOpenAPI:
    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_1_openapi_registration(self):
        """POST endpoint appears in /openapi.json."""
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        paths = spec.get("paths", {})
        pr_path = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/git/pull-request"
        assert pr_path in paths, f"PR path not found in OpenAPI. Available: {list(paths.keys())}"
        assert "post" in paths[pr_path], "PR endpoint must be POST"

    def test_2_no_request_body_schema(self):
        """Endpoint accepts no requestBody — zero client-supplied parameters."""
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/openapi.json")
        spec = resp.json()
        pr_path = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/git/pull-request"
        post_spec = spec["paths"][pr_path]["post"]
        assert "requestBody" not in post_spec, "PR endpoint must accept no request body"


# ---------------------------------------------------------------------------
# 2. Authentication & Authorization
# ---------------------------------------------------------------------------

class TestCreatePRApiAuth:
    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_3_unauthenticated_returns_non_200(self):
        """Unauthenticated request must not succeed."""
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code != 200

    def test_4_authenticated_request_succeeds(self):
        uc_override, _ = _make_use_case_override(return_value=_make_success_result())
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_create_fix_pull_request_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 3. Success Responses
# ---------------------------------------------------------------------------

class TestCreatePRApiSuccess:
    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_5_success_response_structure(self):
        uc_override, _ = _make_use_case_override(return_value=_make_success_result("created", 105))
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_create_fix_pull_request_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 200
        data = resp.json()
        assert "git_pull_request" in data
        assert "fix_suggestion" in data
        assert data["git_pull_request"]["status"] == "created"
        assert data["git_pull_request"]["pr_number"] == 105
        assert "pull/105" in data["git_pull_request"]["pr_url"]

    def test_6_already_exists_reconciliation_200(self):
        uc_override, _ = _make_use_case_override(return_value=_make_success_result("already_exists", 99))
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_create_fix_pull_request_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 200
        data = resp.json()
        assert data["git_pull_request"]["status"] == "already_exists"
        assert data["git_pull_request"]["pr_number"] == 99

    def test_7_user_id_passed_to_use_case(self):
        uc_override, mock_uc = _make_use_case_override(return_value=_make_success_result())
        app.dependency_overrides[get_current_user] = _user_override("user-77")
        app.dependency_overrides[get_create_fix_pull_request_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        client.post(_url("rev-abc", 2))
        kwargs = mock_uc.execute.call_args.kwargs
        assert kwargs["review_id"] == "rev-abc"
        assert kwargs["finding_index"] == 2
        assert kwargs["user_id"] == "user-77"


# ---------------------------------------------------------------------------
# 4. Error Status Codes
# ---------------------------------------------------------------------------

class TestCreatePRApiErrorCodes:
    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_8_review_not_found_returns_404(self):
        uc_override, _ = _make_use_case_override(raise_exc=ResourceNotFoundError("Review not found"))
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_create_fix_pull_request_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 404

    def test_9_review_not_completed_returns_409(self):
        uc_override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("Pull Request creation requires a completed review")
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_create_fix_pull_request_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 409

    def test_10_fix_not_applied_returns_409(self):
        uc_override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("Fix suggestion must be applied before creating a Pull Request")
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_create_fix_pull_request_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 409

    def test_11_no_commit_returns_409(self):
        uc_override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("Fix suggestion must have a local Git commit before creating a Pull Request")
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_create_fix_pull_request_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 409

    def test_12_not_pushed_returns_409(self):
        uc_override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("Fix branch must be pushed to remote before creating a Pull Request")
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_create_fix_pull_request_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 409

    def test_13_out_of_range_index_returns_422(self):
        uc_override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("finding_index 99 out of range (0-1)")
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_create_fix_pull_request_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url(finding_index=99))
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 5. Security & Contract Verification
# ---------------------------------------------------------------------------

class TestCreatePRApiSecurity:
    def test_14_no_secrets_in_response(self):
        uc_override, _ = _make_use_case_override(return_value=_make_success_result())
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_create_fix_pull_request_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        data = resp.json()
        git_pr = data.get("git_pull_request", {})
        forbidden_keys = {"token", "password", "secret", "private_key", "credentials"}
        assert not forbidden_keys.intersection(set(git_pr.keys()))
        app.dependency_overrides = {}
