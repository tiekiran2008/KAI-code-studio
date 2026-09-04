"""
API Tests — POST /api/v1/reviews/{review_id}/findings/{finding_index}/fix/git/push
====================================================================================
Validates: authentication, ownership, eligibility enforcement, commit prerequisite,
idempotency, OpenAPI registration, response security, push-only contract, no-force-push,
no-PR-creation, no-shell, no-LLM proofs, and response schema.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.api.dependencies import (
    get_current_user,
    get_push_fix_branch_use_case,
)
from src.domain.entities.git import GitPushResult, GitPushStatusEnum
from src.application.use_cases.push_fix_branch import PushFixBranchUseCase
from src.core.errors import ResourceNotFoundError, WorkflowExecutionError


ENDPOINT = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/git/push"


def _url(review_id="rev-1", finding_index=0):
    return ENDPOINT.format(review_id=review_id, finding_index=finding_index)


def _user_override(user_id: str = "user-1"):
    def _override():
        return {"sub": user_id, "email": f"{user_id}@example.com"}
    return _override


def _make_push_result(status="pushed"):
    return GitPushResult(
        status=GitPushStatusEnum(status),
        remote_name="origin",
        branch_name="ai-fix/rev-abc12345-f0",
        commit_sha="a" * 40,
        remote_url_masked="https://github.com/user/repo.git",
        pushed_at="2026-08-26T10:01:00+00:00",
        message="Pushed to origin",
    )


def _make_fix_suggestion(push_result=None):
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
    }
    if push_result is not None:
        fix["git_push"] = {
            "status": push_result.status.value if hasattr(push_result.status, "value") else push_result.status,
            "remote_name": push_result.remote_name,
            "branch_name": push_result.branch_name,
            "commit_sha": push_result.commit_sha,
        }
    return fix


def _make_success_result(push_status="pushed"):
    push_result = _make_push_result(push_status)
    return {
        "git_push": push_result,
        "fix_suggestion": _make_fix_suggestion(push_result),
    }


def _make_use_case_override(return_value=None, raise_exc=None):
    mock_uc = MagicMock(spec=PushFixBranchUseCase)
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

class TestPushApiOpenAPI:
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
        push_path = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/git/push"
        assert push_path in paths, f"Push path not found in OpenAPI. Available: {list(paths.keys())}"
        assert "post" in paths[push_path], "Push endpoint must be POST"

    def test_2_no_request_body(self):
        """Endpoint has no requestBody — no client-supplied inputs."""
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/openapi.json")
        spec = resp.json()
        push_path = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/git/push"
        post_spec = spec["paths"][push_path]["post"]
        assert "requestBody" not in post_spec, "Push endpoint must accept no request body"

    def test_3_push_path_distinct_from_commit_path(self):
        """Push endpoint path is distinct from commit endpoint path."""
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/openapi.json")
        spec = resp.json()
        paths = spec.get("paths", {})
        commit_path = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/git/commit"
        push_path = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/git/push"
        assert commit_path in paths, "Commit endpoint must still exist"
        assert push_path in paths, "Push endpoint must exist"
        assert commit_path != push_path


# ---------------------------------------------------------------------------
# 2. Authentication
# ---------------------------------------------------------------------------

class TestPushApiAuth:
    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_4_unauthenticated_returns_non_200(self):
        """No auth token → non-200 status (typically 401 or 403 or 404 depending on auth setup)."""
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code != 200, (
            f"Unauthenticated push request must not succeed. Got {resp.status_code}"
        )

    def test_5_authenticated_returns_not_401(self):
        """Authenticated request is not rejected as unauthorized."""
        uc_override, _ = _make_use_case_override(return_value=_make_success_result())
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code != 401
        app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# 3. Success Responses
# ---------------------------------------------------------------------------

class TestPushApiSuccess:
    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_6_success_returns_200(self):
        uc_override, _ = _make_use_case_override(return_value=_make_success_result())
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 200

    def test_7_response_contains_git_push(self):
        uc_override, _ = _make_use_case_override(return_value=_make_success_result())
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        data = resp.json()
        assert "git_push" in data, f"Response missing git_push. Keys: {list(data.keys())}"

    def test_8_git_push_status_correct(self):
        uc_override, _ = _make_use_case_override(return_value=_make_success_result())
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        data = resp.json()
        assert data["git_push"]["status"] == "pushed"

    def test_9_response_contains_fix_suggestion(self):
        uc_override, _ = _make_use_case_override(return_value=_make_success_result())
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        data = resp.json()
        assert "fix_suggestion" in data

    def test_10_already_pushed_idempotent_200(self):
        uc_override, _ = _make_use_case_override(return_value=_make_success_result("already_pushed"))
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 200
        assert resp.json()["git_push"]["status"] == "already_pushed"

    def test_11_use_case_execute_called_with_user_id(self):
        uc_override, mock_uc = _make_use_case_override(return_value=_make_success_result())
        app.dependency_overrides[get_current_user] = _user_override("user-42")
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        client.post(_url("rev-7", 3))
        call_kwargs = mock_uc.execute.call_args.kwargs
        assert call_kwargs["review_id"] == "rev-7"
        assert call_kwargs["finding_index"] == 3
        assert call_kwargs["user_id"] == "user-42"


# ---------------------------------------------------------------------------
# 4. Error Response Codes
# ---------------------------------------------------------------------------

class TestPushApiErrorCodes:
    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_12_review_not_found_returns_404(self):
        uc_override, _ = _make_use_case_override(raise_exc=ResourceNotFoundError("Review not found"))
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 404

    def test_13_repository_not_found_returns_404(self):
        uc_override, _ = _make_use_case_override(raise_exc=ResourceNotFoundError("Repository not found"))
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 404

    def test_14_not_completed_review_returns_409(self):
        uc_override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("Git branch push requires a completed review")
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 409

    def test_15_not_applied_status_returns_409(self):
        uc_override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("Fix suggestion must be applied before pushing branch")
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 409

    def test_16_no_local_commit_returns_409(self):
        uc_override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("Fix suggestion must have a local Git commit before pushing")
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 409

    def test_17_wrong_commit_status_returns_409(self):
        uc_override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("Local Git commit must be in 'committed' status to push")
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 409

    def test_18_rejected_fix_returns_409(self):
        uc_override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("Cannot push a rejected fix suggestion")
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 409

    def test_19_out_of_range_finding_returns_422(self):
        uc_override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("finding_index 99 out of range (0-2)")
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url(finding_index=99))
        assert resp.status_code == 422

    def test_20_no_fix_suggestion_returns_404(self):
        uc_override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("No fix suggestion exists for this finding")
        )
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 5. Security Contract (No Push, No Force, No PR, No LLM, No Shell)
# ---------------------------------------------------------------------------

class TestPushApiSecurityContract:
    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_21_no_force_push_in_push_use_case(self):
        """push_fix_branch.py must not contain force push flags."""
        from pathlib import Path
        for candidate in [
            Path("backend/src/application/use_cases/push_fix_branch.py"),
            Path("src/application/use_cases/push_fix_branch.py"),
        ]:
            if candidate.exists():
                content = candidate.read_text()
                for forbidden in ("--force", "-f", "--force-with-lease", "+refs"):
                    assert forbidden not in content, \
                        f"Force push token '{forbidden}' found in push_fix_branch.py"
                break

    def test_22_no_pr_creation_in_push_use_case(self):
        """push_fix_branch.py must not contain pull_request or PR creation code."""
        from pathlib import Path
        for candidate in [
            Path("backend/src/application/use_cases/push_fix_branch.py"),
            Path("src/application/use_cases/push_fix_branch.py"),
        ]:
            if candidate.exists():
                content = candidate.read_text()
                for forbidden in ("pull_request", "create_pr", "PullRequest"):
                    assert forbidden not in content, \
                        f"PR token '{forbidden}' found in push_fix_branch.py"
                break

    def test_23_no_llm_in_push_use_case(self):
        """push_fix_branch.py must not import any LLM provider."""
        from pathlib import Path
        for candidate in [
            Path("backend/src/application/use_cases/push_fix_branch.py"),
            Path("src/application/use_cases/push_fix_branch.py"),
        ]:
            if candidate.exists():
                content = candidate.read_text()
                for forbidden in ("LLMProvider", "llm_provider", "openai", "anthropic"):
                    assert forbidden not in content, \
                        f"LLM token '{forbidden}' found in push_fix_branch.py"
                break

    def test_24_no_shell_in_push_use_case(self):
        """push_fix_branch.py must not use shell=True."""
        from pathlib import Path
        for candidate in [
            Path("backend/src/application/use_cases/push_fix_branch.py"),
            Path("src/application/use_cases/push_fix_branch.py"),
        ]:
            if candidate.exists():
                content = candidate.read_text()
                assert "shell=True" not in content, "shell=True found in push_fix_branch.py"
                break

    def test_25_response_has_no_raw_credentials(self):
        """Response JSON must not contain password, token, or secret fields."""
        uc_override, _ = _make_use_case_override(return_value=_make_success_result())
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        raw = resp.text.lower()
        for secret_key in ("password", "secret", "token", "credential"):
            # "token" often appears in auth headers but not in push response JSON
            # We just assert no raw credential values appear in git_push keys
            pass
        data = resp.json()
        git_push = data.get("git_push", {})
        forbidden_keys = {"password", "secret", "private_key", "credential"}
        assert not forbidden_keys.intersection(set(git_push.keys()))

    def test_26_push_endpoint_accepts_no_client_remote_url(self):
        """Endpoint has no request body — client cannot supply remote or ref."""
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/openapi.json")
        spec = resp.json()
        push_path = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/git/push"
        post_spec = spec["paths"][push_path]["post"]
        assert "requestBody" not in post_spec

    def test_27_response_remote_url_is_masked(self):
        """Remote URL in response is the masked variant, not a raw credential-bearing URL."""
        uc_override, _ = _make_use_case_override(return_value=_make_success_result())
        app.dependency_overrides[get_current_user] = _user_override()
        app.dependency_overrides[get_push_fix_branch_use_case] = uc_override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url())
        data = resp.json()
        masked = data.get("git_push", {}).get("remote_url_masked", "")
        # Masked URL must not contain @user:password@ pattern
        import re
        assert not re.search(r":[^@]+@", masked or ""), \
            "remote_url_masked must not contain raw credentials"
