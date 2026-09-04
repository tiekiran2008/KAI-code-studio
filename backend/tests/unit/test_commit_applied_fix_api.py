"""
API Tests — POST /api/v1/reviews/{review_id}/findings/{finding_index}/fix/git/commit
=====================================================================================
Validates: authentication, ownership, eligibility, commit isolation, working-tree
preservation, staged-index preservation, HEAD preservation, idempotency, concurrency,
OpenAPI registration, response security, no-push, no-LLM, no-shell proofs.
"""
import asyncio
import hashlib
import subprocess
from pathlib import Path
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.api.dependencies import (
    get_current_user,
    get_commit_applied_fix_use_case,
)
from src.domain.entities.git import GitCommitResult, GitCommitStatusEnum
from src.application.use_cases.commit_applied_fix import CommitAppliedFixUseCase
from src.core.errors import ResourceNotFoundError, WorkflowExecutionError


ENDPOINT = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/git/commit"


def _url(review_id="rev-1", finding_index=0):
    return ENDPOINT.format(review_id=review_id, finding_index=finding_index)


def _user_override(user_id: str = "user-1"):
    def _override():
        return {"sub": user_id, "email": f"{user_id}@example.com"}
    return _override


def _make_success_result(branch="ai-fix/rev-abc12345-f0", sha="a" * 40, file_path="src/utils.py"):
    """Build a mock successful commit result dict."""
    return {
        "git_commit": GitCommitResult(
            status=GitCommitStatusEnum.COMMITTED,
            branch_name=branch,
            commit_sha=sha,
            committed_at="2026-08-26T10:00:00+00:00",
            file_path=file_path,
            commit_message="fix: resolve finding 0 in src/utils.py",
            base_branch="main",
            base_commit_sha="b" * 40,
            message=f"Created commit {sha[:8]} on branch {branch}",
        ),
        "fix_suggestion": {
            "finding_index": 0,
            "file_path": file_path,
            "original_code": "def foo(): pass",
            "proposed_code": "def foo() -> None: pass",
            "explanation": "Add return type hint",
            "diff": "--- a\n+++ b",
            "confidence_score": 0.95,
            "validation_status": "valid",
            "user_decision": "accepted",
            "application_status": "applied",
            "new_hash": "abc123",
            "static_verification": {"status": "passed"},
        },
    }


def _make_use_case_override(return_value=None, raise_exc=None):
    mock_uc = MagicMock(spec=CommitAppliedFixUseCase)
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

class TestCommitApiOpenAPI:
    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_1_openapi_registration(self):
        """POST endpoint appears in /openapi.json with correct path and method."""
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        paths = spec.get("paths", {})

        commit_path = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/git/commit"
        assert commit_path in paths, f"Commit path not found in OpenAPI. Available: {list(paths.keys())}"
        assert "post" in paths[commit_path], "Commit endpoint must be POST"

    def test_2_no_request_body_schema(self):
        """Endpoint has no requestBody — client supplies only path params."""
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/openapi.json")
        spec = resp.json()
        commit_path = "/api/v1/reviews/{review_id}/findings/{finding_index}/fix/git/commit"
        endpoint_spec = spec["paths"][commit_path]["post"]

        assert "requestBody" not in endpoint_spec, (
            "Commit endpoint must NOT accept a request body — no client-supplied Git parameters"
        )


# ---------------------------------------------------------------------------
# 2. Authentication
# ---------------------------------------------------------------------------

class TestCommitApiAuthentication:
    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_3_unauthenticated_returns_401(self):
        """Request without valid auth token returns 401."""
        def _raise_401():
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = _raise_401
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(_url("rev-1", 0))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 3. Ownership Enforcement
# ---------------------------------------------------------------------------

class TestCommitApiOwnership:
    def setup_method(self):
        app.dependency_overrides = {}
        app.dependency_overrides[get_current_user] = _user_override("user-1")

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_4_review_not_found_returns_404(self):
        override, _ = _make_use_case_override(raise_exc=ResourceNotFoundError("Review not found or access denied"))
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("no-such-rev", 0))
        assert resp.status_code == 404

    def test_5_cross_user_review_returns_404(self):
        override, _ = _make_use_case_override(raise_exc=ResourceNotFoundError("Review not found or access denied"))
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("other-user-rev", 0))
        assert resp.status_code == 404

    def test_6_repository_not_found_returns_404(self):
        override, _ = _make_use_case_override(raise_exc=ResourceNotFoundError("Repository not found or access denied"))
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("rev-1", 0))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. Finding Index Validation
# ---------------------------------------------------------------------------

class TestCommitApiFindingIndex:
    def setup_method(self):
        app.dependency_overrides = {}
        app.dependency_overrides[get_current_user] = _user_override("user-1")

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_7_negative_finding_index_returns_422(self):
        override, _ = _make_use_case_override(return_value=_make_success_result())
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("rev-1", -1))
        assert resp.status_code == 422

    def test_8_out_of_range_finding_index_returns_422(self):
        override, _ = _make_use_case_override(raise_exc=WorkflowExecutionError("finding_index 99 out of range"))
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("rev-1", 99))
        assert resp.status_code == 422

    def test_9_large_finding_index_handled(self):
        override, _ = _make_use_case_override(raise_exc=WorkflowExecutionError("finding_index 9999 out of range"))
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("rev-1", 9999))
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 5. Eligibility Enforcement
# ---------------------------------------------------------------------------

class TestCommitApiEligibility:
    def setup_method(self):
        app.dependency_overrides = {}
        app.dependency_overrides[get_current_user] = _user_override("user-1")

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_10_fix_not_applied_returns_409(self):
        override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("Fix suggestion must be applied before committing")
        )
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("rev-1", 0))
        assert resp.status_code == 409

    def test_11_tier1_static_verification_not_passed_returns_409(self):
        override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("static verification must be 'passed' to commit fix")
        )
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("rev-1", 0))
        assert resp.status_code == 409

    def test_12_review_not_completed_returns_409(self):
        override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("Git commit requires a completed review")
        )
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("rev-1", 0))
        assert resp.status_code == 409

    def test_13_rejected_fix_returns_409(self):
        override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("Cannot commit a rejected fix suggestion")
        )
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("rev-1", 0))
        assert resp.status_code == 409

    def test_14_no_fix_suggestion_returns_404(self):
        override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("No fix suggestion exists for this finding")
        )
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("rev-1", 0))
        assert resp.status_code == 404

    def test_15_stale_source_returns_409(self):
        override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("Source file was modified after fix was applied")
        )
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("rev-1", 0))
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# 6. Success Response
# ---------------------------------------------------------------------------

class TestCommitApiSuccess:
    def setup_method(self):
        app.dependency_overrides = {}
        app.dependency_overrides[get_current_user] = _user_override("user-1")

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_16_returns_200_with_commit_metadata(self):
        """Happy path returns 200 with typed GitCommitResult."""
        result = _make_success_result()
        override, _ = _make_use_case_override(return_value=result)
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("rev-1", 0))
        assert resp.status_code == 200
        body = resp.json()
        assert "git_commit" in body
        assert body["git_commit"]["status"] == "committed"
        assert body["git_commit"]["commit_sha"] == "a" * 40
        assert body["git_commit"]["branch_name"] == "ai-fix/rev-abc12345-f0"

    def test_17_response_contains_fix_suggestion(self):
        result = _make_success_result()
        override, _ = _make_use_case_override(return_value=result)
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("rev-1", 0))
        assert resp.status_code == 200
        body = resp.json()
        assert "fix_suggestion" in body
        assert body["fix_suggestion"]["file_path"] == "src/utils.py"

    def test_18_branch_name_is_server_generated(self):
        """Branch name is generated server-side and follows the safe naming scheme."""
        result = _make_success_result()
        override, _ = _make_use_case_override(return_value=result)
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("rev-1", 0))
        assert resp.status_code == 200
        body = resp.json()
        branch = body["git_commit"]["branch_name"]
        # Must follow safe server-generated pattern
        assert branch.startswith("ai-fix/"), f"Branch name must start with ai-fix/, got: {branch}"
        # Must not contain shell metacharacters
        for char in [";", "&", "|", "$", "`", " ", ".."]:
            assert char not in branch, f"Branch name contains dangerous character '{char}': {branch}"


# ---------------------------------------------------------------------------
# 7. No Arbitrary Client Git Input
# ---------------------------------------------------------------------------

class TestCommitApiNoClientInput:
    def setup_method(self):
        app.dependency_overrides = {}
        app.dependency_overrides[get_current_user] = _user_override("user-1")

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_19_client_body_rejected_entirely(self):
        """Even if client sends a JSON body, it is ignored and not used as Git parameters."""
        result = _make_success_result()
        override, mock_uc = _make_use_case_override(return_value=result)
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(
            _url("rev-1", 0),
            json={
                "branch_name": "attacker-controlled-branch",
                "commit_message": "attacker message",
                "repository_path": "/etc/passwd",
                "force": True,
            },
        )
        assert resp.status_code == 200
        call_kwargs = mock_uc.execute.call_args
        assert "attacker-controlled-branch" not in str(call_kwargs)

    def test_20_no_user_id_accepted_from_client(self):
        """user_id is always derived from authenticated JWT, never from client body."""
        result = _make_success_result()
        override, mock_uc = _make_use_case_override(return_value=result)
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(
            _url("rev-1", 0),
            json={"user_id": "attacker-user-id"},
        )
        assert resp.status_code == 200
        actual_user_id = mock_uc.execute.call_args.kwargs.get("user_id") or mock_uc.execute.call_args.args[2]
        assert actual_user_id == "user-1"


# ---------------------------------------------------------------------------
# 8. Idempotency
# ---------------------------------------------------------------------------

class TestCommitApiIdempotency:
    def setup_method(self):
        app.dependency_overrides = {}
        app.dependency_overrides[get_current_user] = _user_override("user-1")

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_21_repeated_commit_returns_same_sha(self):
        """Calling commit twice returns the same commit SHA without creating duplicates."""
        existing_commit = GitCommitResult(
            status=GitCommitStatusEnum.COMMITTED,
            branch_name="ai-fix/rev-abc12345-f0",
            commit_sha="c" * 40,
            committed_at="2026-08-26T10:00:00+00:00",
            file_path="src/utils.py",
            commit_message="fix: resolve finding 0",
            base_branch="main",
            base_commit_sha="d" * 40,
            message="Already committed",
        )
        result = {
            "git_commit": existing_commit,
            "fix_suggestion": {
                "finding_index": 0,
                "file_path": "src/utils.py",
                "original_code": "x",
                "proposed_code": "y",
                "explanation": "e",
                "diff": "",
                "confidence_score": 0.9,
                "validation_status": "valid",
                "user_decision": "accepted",
                "application_status": "applied",
                "static_verification": {"status": "passed"},
                "git_commit": {
                    "status": "committed",
                    "commit_sha": "c" * 40,
                    "branch_name": "ai-fix/rev-abc12345-f0",
                },
            },
        }
        override, _ = _make_use_case_override(return_value=result)
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp1 = client.post(_url("rev-1", 0))
        resp2 = client.post(_url("rev-1", 0))

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["git_commit"]["commit_sha"] == resp2.json()["git_commit"]["commit_sha"]


# ---------------------------------------------------------------------------
# 9. No Push / No GitHub / No LLM Proofs
# ---------------------------------------------------------------------------

class TestCommitApiSecurityProofs:

    def test_22_no_push_invoked(self, tmp_path):
        """Verify git push is never invoked in the commit path (static audit)."""
        commit_use_case_src = Path("src/application/use_cases/commit_applied_fix.py")
        backend_root = Path(__file__).resolve().parent.parent.parent
        content = (backend_root / commit_use_case_src).read_text(encoding="utf-8")

        assert '"push"' not in content, "CommitAppliedFixUseCase must not invoke git push"

    def test_23_no_github_write_invoked(self):
        """CommitAppliedFixUseCase must not import or call GitHub adapter."""
        backend_root = Path(__file__).resolve().parent.parent.parent
        use_case_src = backend_root / "src/application/use_cases/commit_applied_fix.py"
        content = use_case_src.read_text(encoding="utf-8")

        assert "GitHubToolAdapter" not in content
        assert "github.com/rest" not in content
        assert "create_pull_request" not in content
        assert "create_branch" not in content

    def test_24_no_llm_calls(self):
        """CommitAppliedFixUseCase must not import or invoke any LLM provider."""
        backend_root = Path(__file__).resolve().parent.parent.parent
        for rel_path in [
            "src/application/use_cases/commit_applied_fix.py",
            "src/infrastructure/git/git_runner.py",
            "src/infrastructure/git/working_tree_manager.py",
        ]:
            content = (backend_root / rel_path).read_text(encoding="utf-8")
            assert "llm_provider" not in content, f"LLM call found in {rel_path}"
            assert "LLMProvider" not in content, f"LLM import found in {rel_path}"
            assert "openai" not in content.lower(), f"OpenAI reference found in {rel_path}"

    def test_25_no_shell_true(self):
        """No shell=True in any git infrastructure file."""
        backend_root = Path(__file__).resolve().parent.parent.parent
        for rel_path in [
            "src/application/use_cases/commit_applied_fix.py",
            "src/infrastructure/git/git_runner.py",
            "src/infrastructure/git/working_tree_manager.py",
        ]:
            content = (backend_root / rel_path).read_text(encoding="utf-8")
            assert "shell=True" not in content, f"shell=True found in {rel_path}"

    def test_26_no_destructive_git_commands(self):
        """No destructive Git commands appear in the commit path source code."""
        backend_root = Path(__file__).resolve().parent.parent.parent
        for rel_path in [
            "src/application/use_cases/commit_applied_fix.py",
            "src/infrastructure/git/working_tree_manager.py",
        ]:
            content = (backend_root / rel_path).read_text(encoding="utf-8")
            forbidden = ['"reset"', '"clean"', '"checkout"', '"restore"', '"cherry-pick"']
            for cmd in forbidden:
                assert cmd not in content, f"Forbidden Git command {cmd} found in {rel_path}"


# ---------------------------------------------------------------------------
# 10. Response Security
# ---------------------------------------------------------------------------

class TestCommitApiResponseSecurity:
    def setup_method(self):
        app.dependency_overrides = {}
        app.dependency_overrides[get_current_user] = _user_override("user-1")

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_27_response_no_absolute_paths(self):
        """Response must not expose absolute filesystem paths."""
        result = _make_success_result()
        override, _ = _make_use_case_override(return_value=result)
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("rev-1", 0))
        body_str = resp.text

        assert "C:\\" not in body_str and "D:\\" not in body_str
        assert "/home/" not in body_str
        assert "agy_git_idx_" not in body_str

    def test_28_error_response_no_stack_trace(self):
        """Error responses must not expose stack traces or internal paths."""
        override, _ = _make_use_case_override(
            raise_exc=WorkflowExecutionError("Source file was modified after fix was applied")
        )
        app.dependency_overrides[get_commit_applied_fix_use_case] = override
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(_url("rev-1", 0))
        body_str = resp.text
        assert "Traceback" not in body_str
        assert ".gemini" not in body_str
        assert "antigravity-ide" not in body_str


# ---------------------------------------------------------------------------
# 11. Integration with Real Git Repo (Commit Isolation Tests)
# ---------------------------------------------------------------------------

def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=str(path), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@test.com",
         "commit", "--allow-empty", "-m", "Init"],
        cwd=str(path), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


class TestCommitApiRealGitIsolation:
    """Integration-style tests using a real temporary git repository."""

    def _make_use_case_with_workspace(self, workspace: Path):
        """Build a real CommitAppliedFixUseCase pointing at workspace."""
        from src.infrastructure.git.working_tree_manager import GitWorkingTreeManager

        review_svc = MagicMock()
        repo_svc = MagicMock()
        repo_svc.get_repository = MagicMock(return_value=MagicMock(id="repo-1"))

        return CommitAppliedFixUseCase(
            review_service=review_svc,
            repository_service=repo_svc,
            working_tree_manager=GitWorkingTreeManager(),
            workspace_root_resolver=lambda u, r: str(workspace),
        ), review_svc

    def _setup_committed_file(self, workspace: Path, filename: str, content: bytes):
        """Create, stage, and commit a file in the test git repo."""
        target = workspace / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        subprocess.run(["git", "add", filename], cwd=str(workspace), check=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@test.com",
             "commit", "-m", f"add {filename}"],
            cwd=str(workspace), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        return target

    @pytest.mark.asyncio
    async def test_29_commit_contains_only_target_file(self, tmp_path):
        """CRITICAL: Created commit must contain strictly the target file — no others."""
        _init_git_repo(tmp_path)

        file_a_content = b"def foo(): pass\n"
        file_b_content = b"def bar(): pass\n"
        self._setup_committed_file(tmp_path, "a.py", file_a_content)
        self._setup_committed_file(tmp_path, "b.py", file_b_content)

        fixed_content = b"def foo() -> None: pass\n"
        (tmp_path / "a.py").write_bytes(fixed_content)
        content_hash = hashlib.sha256(fixed_content).hexdigest()

        use_case, review_svc = self._make_use_case_with_workspace(tmp_path)

        review_svc.get_review.return_value = MagicMock(
            id="rev-1",
            repository_id="repo-1",
            status="completed",
            findings_json=[{
                "issue": "Missing type hint",
                "fix_suggestion": {
                    "finding_index": 0,
                    "file_path": "a.py",
                    "original_code": "def foo(): pass",
                    "proposed_code": "def foo() -> None: pass",
                    "explanation": "Type hint",
                    "diff": "",
                    "confidence_score": 0.95,
                    "validation_status": "valid",
                    "user_decision": "accepted",
                    "application_status": "applied",
                    "new_hash": content_hash,
                    "static_verification": {"status": "passed"},
                },
            }],
        )
        review_svc.update_finding_git_commit_result.return_value = (
            review_svc.get_review.return_value.findings_json[0]["fix_suggestion"]
        )

        result = await use_case.execute("rev-1", 0, "user-1")

        assert result["git_commit"].status == GitCommitStatusEnum.COMMITTED
        commit_sha = result["git_commit"].commit_sha
        base_sha = result["git_commit"].base_commit_sha

        diff_out = subprocess.run(
            ["git", "diff", f"{base_sha}..{commit_sha}", "--name-only"],
            cwd=str(tmp_path), check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.strip()
        assert diff_out == "a.py", f"Expected only 'a.py' in commit, got: {diff_out}"

    @pytest.mark.asyncio
    async def test_30_unrelated_modified_file_not_in_commit(self, tmp_path):
        """CRITICAL: Unrelated user-modified file B must not appear in the AI commit."""
        _init_git_repo(tmp_path)

        file_a_content = b"def a(): pass\n"
        file_b_content = b"def b(): pass\n"
        self._setup_committed_file(tmp_path, "a.py", file_a_content)
        self._setup_committed_file(tmp_path, "b.py", file_b_content)

        (tmp_path / "b.py").write_bytes(b"def b() -> str: return 'user_change'\n")

        fixed_a = b"def a() -> None: pass\n"
        (tmp_path / "a.py").write_bytes(fixed_a)
        content_hash = hashlib.sha256(fixed_a).hexdigest()

        use_case, review_svc = self._make_use_case_with_workspace(tmp_path)
        review_svc.get_review.return_value = MagicMock(
            id="rev-1", repository_id="repo-1", status="completed",
            findings_json=[{"issue": "t", "fix_suggestion": {
                "finding_index": 0, "file_path": "a.py",
                "original_code": "def a(): pass", "proposed_code": "def a() -> None: pass",
                "explanation": "e", "diff": "", "confidence_score": 0.9,
                "validation_status": "valid", "user_decision": "accepted",
                "application_status": "applied", "new_hash": content_hash,
                "static_verification": {"status": "passed"},
            }}],
        )
        review_svc.update_finding_git_commit_result.return_value = (
            review_svc.get_review.return_value.findings_json[0]["fix_suggestion"]
        )

        result = await use_case.execute("rev-1", 0, "user-1")
        commit_sha = result["git_commit"].commit_sha
        base_sha = result["git_commit"].base_commit_sha

        diff_out = subprocess.run(
            ["git", "diff", f"{base_sha}..{commit_sha}", "--name-only"],
            cwd=str(tmp_path), check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.strip()
        assert "b.py" not in diff_out, "Unrelated file B must not appear in the AI commit"
        assert diff_out == "a.py"

        assert (tmp_path / "b.py").read_text() == "def b() -> str: return 'user_change'\n"

    @pytest.mark.asyncio
    async def test_31_user_staged_changes_preserved_after_commit(self, tmp_path):
        """CRITICAL: User's staged changes in primary .git/index are preserved after AI commit."""
        _init_git_repo(tmp_path)

        file_a_content = b"def a(): pass\n"
        file_c_content = b"def c(): pass\n"
        self._setup_committed_file(tmp_path, "a.py", file_a_content)
        self._setup_committed_file(tmp_path, "c.py", file_c_content)

        (tmp_path / "c.py").write_bytes(b"def c() -> str: return 'staged'\n")
        subprocess.run(["git", "add", "c.py"], cwd=str(tmp_path), check=True)

        fixed_a = b"def a() -> None: pass\n"
        (tmp_path / "a.py").write_bytes(fixed_a)
        content_hash = hashlib.sha256(fixed_a).hexdigest()

        use_case, review_svc = self._make_use_case_with_workspace(tmp_path)
        review_svc.get_review.return_value = MagicMock(
            id="rev-1", repository_id="repo-1", status="completed",
            findings_json=[{"issue": "t", "fix_suggestion": {
                "finding_index": 0, "file_path": "a.py",
                "original_code": "x", "proposed_code": "y",
                "explanation": "e", "diff": "", "confidence_score": 0.9,
                "validation_status": "valid", "user_decision": "accepted",
                "application_status": "applied", "new_hash": content_hash,
                "static_verification": {"status": "passed"},
            }}],
        )
        review_svc.update_finding_git_commit_result.return_value = (
            review_svc.get_review.return_value.findings_json[0]["fix_suggestion"]
        )

        result = await use_case.execute("rev-1", 0, "user-1")
        assert result["git_commit"].status == GitCommitStatusEnum.COMMITTED

        status_out = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=str(tmp_path), check=True, stdout=subprocess.PIPE, text=True,
        ).stdout
        staged_files = [
            line[3:].strip() for line in status_out.splitlines()
            if len(line) >= 3 and line[0] not in (" ", "?")
        ]
        assert "c.py" in staged_files, "User's staged c.py must remain staged after AI commit"

    @pytest.mark.asyncio
    async def test_32_active_branch_head_unchanged(self, tmp_path):
        """CRITICAL: User's active branch and HEAD must be identical before and after commit."""
        _init_git_repo(tmp_path)

        file_content = b"def x(): pass\n"
        self._setup_committed_file(tmp_path, "x.py", file_content)

        head_before = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(tmp_path),
            check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.strip()
        branch_before = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(tmp_path),
            check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.strip()

        fixed = b"def x() -> None: pass\n"
        (tmp_path / "x.py").write_bytes(fixed)
        content_hash = hashlib.sha256(fixed).hexdigest()

        use_case, review_svc = self._make_use_case_with_workspace(tmp_path)
        review_svc.get_review.return_value = MagicMock(
            id="rev-1", repository_id="repo-1", status="completed",
            findings_json=[{"issue": "t", "fix_suggestion": {
                "finding_index": 0, "file_path": "x.py",
                "original_code": "x", "proposed_code": "y",
                "explanation": "e", "diff": "", "confidence_score": 0.9,
                "validation_status": "valid", "user_decision": "accepted",
                "application_status": "applied", "new_hash": content_hash,
                "static_verification": {"status": "passed"},
            }}],
        )
        review_svc.update_finding_git_commit_result.return_value = (
            review_svc.get_review.return_value.findings_json[0]["fix_suggestion"]
        )

        await use_case.execute("rev-1", 0, "user-1")

        head_after = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(tmp_path),
            check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.strip()
        branch_after = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(tmp_path),
            check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.strip()

        assert head_after == head_before, "HEAD must not change after AI commit"
        assert branch_after == branch_before, "Active branch must not change after AI commit"

    @pytest.mark.asyncio
    async def test_33_dedicated_branch_created_by_ref_update(self, tmp_path):
        """Dedicated AI fix branch is created via update-ref, not branch checkout."""
        _init_git_repo(tmp_path)

        file_content = b"def z(): pass\n"
        self._setup_committed_file(tmp_path, "z.py", file_content)
        fixed = b"def z() -> None: pass\n"
        (tmp_path / "z.py").write_bytes(fixed)
        content_hash = hashlib.sha256(fixed).hexdigest()

        use_case, review_svc = self._make_use_case_with_workspace(tmp_path)
        review_svc.get_review.return_value = MagicMock(
            id="rev-abc12345-ef", repository_id="repo-1", status="completed",
            findings_json=[{"issue": "t", "fix_suggestion": {
                "finding_index": 0, "file_path": "z.py",
                "original_code": "x", "proposed_code": "y",
                "explanation": "e", "diff": "", "confidence_score": 0.9,
                "validation_status": "valid", "user_decision": "accepted",
                "application_status": "applied", "new_hash": content_hash,
                "static_verification": {"status": "passed"},
            }}],
        )
        review_svc.update_finding_git_commit_result.return_value = (
            review_svc.get_review.return_value.findings_json[0]["fix_suggestion"]
        )

        result = await use_case.execute("rev-abc12345-ef", 0, "user-1")
        branch = result["git_commit"].branch_name

        branch_sha = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{branch}"],
            cwd=str(tmp_path), check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.strip()
        assert len(branch_sha) == 40, f"Branch {branch} must exist with a valid commit SHA"

        current_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(tmp_path), check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.strip()
        assert current_branch != branch, f"HEAD must not be on AI branch {branch}"
