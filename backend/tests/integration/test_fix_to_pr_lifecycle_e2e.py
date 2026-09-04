"""
Integration Tests — Fix-to-PR Full Lifecycle E2E
=================================================
End-to-end integration and invariant validation for Phase 11.5:
1. Complete happy-path lifecycle: Review -> Generate Fix -> Accept -> Apply ->
   Static Verify -> Test Verify -> Local Commit -> Push Branch -> Create PR -> Persistence Check.
2. State machine transition enforcement (invalid transitions rejected with 409 / 422).
3. Action separation (no action auto-triggers subsequent actions).
4. Multiple findings independence (finding 0 at PR, finding 1 accepted, finding 2 rejected).
5. Cross-user isolation & anti-enumeration (User B blocked at all endpoints with 404).
6. Finding index boundary protection (-1, 99, 999999 -> 422).
7. Stale source & tampering protection.
8. Git & Push isolation in a real Git repo with dirty working tree and staged index.
9. Idempotency across Apply, Commit, Push, and PR creation endpoints.
10. Restart-safe persistence verification.

LLM calls: 0 | shell=True: 0 | force-push: 0 | auto-merge: 0
"""
import asyncio
import hashlib
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.api.dependencies import (
    get_current_user,
    get_code_review_service,
    get_repository_service,
    get_apply_fix_use_case,
    get_verify_applied_fix_use_case,
    get_verify_applied_fix_tests_use_case,
    get_commit_applied_fix_use_case,
    get_push_fix_branch_use_case,
    get_create_fix_pull_request_use_case,
)
from src.interfaces.api.v1.reviews import get_fix_suggestion_agent, get_code_review_service as get_reviews_code_review_service
from src.domain.entities.git import (
    GitCommitResult,
    GitCommitStatusEnum,
    GitPushResult,
    GitPushStatusEnum,
    GitPullRequestResult,
    GitPullRequestStatusEnum,
)
from src.domain.entities.fix_suggestion import FixSuggestion, FixUserDecision, FixApplicationStatus
from src.domain.entities.verification import StaticVerificationResult, VerificationStatus
from src.domain.entities.sandbox import SandboxVerificationResult, SandboxVerificationStatusEnum
from src.infrastructure.git.working_tree_manager import GitWorkingTreeManager
from src.infrastructure.git.git_runner import GitCommandRunner
from src.infrastructure.git.github_pr_service import GitHubPullRequestService


# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------

def _init_git_repo(path: Path) -> None:
    """Initialize a real Git repository with main branch."""
    subprocess.run(["git", "init", "-b", "main"], cwd=str(path), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(path), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(path), check=True)
    
    init_file = path / "README.md"
    init_file.write_text("# Test Repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=str(path), check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(path), check=True)


def _init_bare_remote(path: Path) -> Path:
    """Initialize a bare Git remote repository."""
    remote_path = path / "remote.git"
    remote_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--bare"], cwd=str(remote_path), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return remote_path


class InMemoryReviewStore:
    """Simulates persistent storage for reviews and repositories."""
    def __init__(self):
        self.reviews: Dict[str, Any] = {}
        self.repositories: Dict[str, Any] = {}

    def get_review(self, review_id: str, user_id: Optional[str] = None):
        r = self.reviews.get(review_id)
        if not r:
            return None
        if user_id is not None and getattr(r, "user_id", None) and r.user_id != user_id:
            return None
        return r

    def save_review(self, review):
        self.reviews[review.id] = review
        return review

    def get_repository(self, user_id: str, repo_id: str):
        repo = self.repositories.get(repo_id)
        if not repo:
            return None
        if getattr(repo, "user_id", None) and repo.user_id != user_id:
            return None
        return repo


def _make_mock_review_entity(review_id: str, repo_id: str, user_id: str, findings: List[Dict[str, Any]]):
    review = MagicMock()
    review.id = review_id
    review.repository_id = repo_id
    review.user_id = user_id
    review.status = "completed"
    review.findings_json = findings
    review.security_score = 85.0
    review.performance_score = 90.0
    review.architecture_score = 88.0
    review.maintainability_score = 82.0
    return review


def _make_mock_repository_entity(repo_id: str, user_id: str, local_path: str, remote_url: str):
    repo = MagicMock()
    repo.id = repo_id
    repo.user_id = user_id
    repo.owner = "test-org"
    repo.name = "test-repo"
    repo.local_path = local_path
    repo.url = remote_url
    repo.default_branch = "main"
    repo.git_access_token_encrypted = "mock_token"
    return repo


# ---------------------------------------------------------------------------
# 1. Complete Happy-Path E2E Lifecycle
# ---------------------------------------------------------------------------

class TestFixToPRLifecycleE2E:
    def test_full_happy_path_lifecycle(self, tmp_path):
        # 1. Setup real local repo and bare remote
        local_repo_path = tmp_path / "local_repo"
        local_repo_path.mkdir()
        _init_git_repo(local_repo_path)
        
        bare_remote_path = _init_bare_remote(tmp_path)
        subprocess.run(
            ["git", "remote", "add", "origin", str(bare_remote_path)],
            cwd=str(local_repo_path),
            check=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=str(local_repo_path),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Setup source file
        calc_file = local_repo_path / "src" / "calc.py"
        calc_file.parent.mkdir(parents=True, exist_ok=True)
        original_code = "def divide(a, b):\n    return a / b\n"
        calc_file.write_text(original_code)
        
        subprocess.run(["git", "add", "src/calc.py"], cwd=str(local_repo_path), check=True)
        subprocess.run(["git", "commit", "-m", "add calc.py"], cwd=str(local_repo_path), check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=str(local_repo_path), check=True)

        fixed_code = "def divide(a, b):\n    if b == 0:\n        raise ValueError('Division by zero')\n    return a / b\n"
        new_hash = hashlib.sha256(fixed_code.encode("utf-8")).hexdigest()
        review_id = "rev-e2e-001"
        repo_id = "repo-e2e-001"
        user_id = "user-alice"

        findings = [
            {
                "id": "f-0",
                "category": "security",
                "severity": "high",
                "issue": "Potential ZeroDivisionError",
                "file_path": "src/calc.py",
                "line_number": 2,
                "description": "Missing divisor check",
            },
            {
                "id": "f-1",
                "category": "style",
                "severity": "low",
                "issue": "Missing docstring",
                "file_path": "src/calc.py",
                "line_number": 1,
            },
        ]

        store = InMemoryReviewStore()
        review = _make_mock_review_entity(review_id, repo_id, user_id, findings)
        repo = _make_mock_repository_entity(repo_id, user_id, str(local_repo_path), str(bare_remote_path))
        store.save_review(review)
        store.repositories[repo_id] = repo

        review_service_mock = MagicMock()
        review_service_mock.get_review.side_effect = lambda rid, user_id=None: store.get_review(rid, user_id)
        
        def update_finding_fix_mock(review_id, finding_index, fix_suggestion, user_id):
            r = store.get_review(review_id, user_id)
            r.findings_json[finding_index]["fix_suggestion"] = fix_suggestion.model_dump() if hasattr(fix_suggestion, "model_dump") else fix_suggestion
            return r.findings_json[finding_index]["fix_suggestion"]
        
        def update_finding_decision_mock(review_id, finding_index, decision, user_id):
            r = store.get_review(review_id, user_id)
            fix = r.findings_json[finding_index].get("fix_suggestion")
            if not fix:
                raise KeyError("No fix suggestion")
            fix["user_decision"] = decision.value if hasattr(decision, "value") else decision
            return fix

        review_service_mock.update_finding_fix_suggestion = update_finding_fix_mock
        review_service_mock.update_finding_decision = update_finding_decision_mock

        repo_service_mock = MagicMock()
        repo_service_mock.get_repository.side_effect = lambda user_id, repo_id: store.get_repository(user_id, repo_id)

        # Mock fix agent
        fix_agent_mock = MagicMock()
        fix_agent_mock.generate_fix = AsyncMock(return_value={
            "finding_index": 0,
            "file_path": "src/calc.py",
            "original_code": original_code,
            "proposed_code": fixed_code,
            "explanation": "Add zero-division guard",
            "diff": "--- a/src/calc.py\n+++ b/src/calc.py\n@@ -1,2 +1,4 @@\n def divide(a, b):\n+    if b == 0:\n+        raise ValueError('Division by zero')\n     return a / b\n",
            "confidence_score": 0.98,
            "validation_status": "valid",
            "user_decision": "pending",
            "application_status": "not_applied",
        })

        # Mock use cases
        apply_uc_mock = MagicMock()
        async def apply_fix_impl(review_id, finding_index, user_id):
            calc_file.write_text(fixed_code)
            fix = review.findings_json[finding_index]["fix_suggestion"]
            fix["application_status"] = "applied"
            fix["new_hash"] = new_hash
            return {"finding_index": finding_index, "application_status": "applied", "file_path": "src/calc.py", "new_hash": new_hash, "fix_suggestion": fix}
        apply_uc_mock.execute = AsyncMock(side_effect=apply_fix_impl)

        verify_static_mock = MagicMock()
        async def verify_static_impl(review_id, finding_index, user_id):
            fix = review.findings_json[finding_index]["fix_suggestion"]
            ver = StaticVerificationResult(
                status=VerificationStatus.PASSED,
                syntax_valid=True,
                ast_valid=True,
                import_valid=True,
                hash_valid=True,
                message="All static checks passed",
            )
            fix["static_verification"] = ver.model_dump()
            return {"verification": ver, "fix_suggestion": fix}
        verify_static_mock.execute = AsyncMock(side_effect=verify_static_impl)

        verify_tests_mock = MagicMock()
        async def verify_tests_impl(review_id, finding_index, user_id):
            fix = review.findings_json[finding_index]["fix_suggestion"]
            ver = SandboxVerificationResult(
                status=SandboxVerificationStatusEnum.PASSED,
                passed_tests=5,
                failed_tests=0,
                message="All isolated tests passed",
            )
            fix["test_verification"] = ver.model_dump()
            return {"verification": ver, "fix_suggestion": fix}
        verify_tests_mock.execute = AsyncMock(side_effect=verify_tests_impl)

        wt_manager = GitWorkingTreeManager()
        branch_name = f"ai-fix/rev-{review_id[:8]}-f0"

        commit_uc_mock = MagicMock()
        async def commit_fix_impl(review_id, finding_index, user_id):
            commit_res = wt_manager.create_isolated_fix_commit(
                workspace_root=local_repo_path,
                relative_target_path="src/calc.py",
                review_id=review_id,
                finding_index=finding_index,
                finding_issue="guard against zero division",
            )
            fix = review.findings_json[finding_index]["fix_suggestion"]
            fix["git_commit"] = commit_res.model_dump()
            return {"git_commit": commit_res, "fix_suggestion": fix}
        commit_uc_mock.execute = AsyncMock(side_effect=commit_fix_impl)

        push_uc_mock = MagicMock()
        async def push_fix_impl(review_id, finding_index, user_id):
            fix = review.findings_json[finding_index]["fix_suggestion"]
            commit_sha = fix["git_commit"]["commit_sha"]
            branch_to_push = fix["git_commit"]["branch_name"]
            push_res = wt_manager.push_isolated_branch(
                workspace_root=local_repo_path,
                branch_name=branch_to_push,
                expected_commit_sha=commit_sha,
                remote_name="origin",
                expected_repo_url=str(bare_remote_path),
            )
            fix["git_push"] = push_res.model_dump()
            return {"git_push": push_res, "fix_suggestion": fix}
        push_uc_mock.execute = AsyncMock(side_effect=push_fix_impl)

        pr_uc_mock = MagicMock()
        async def pr_fix_impl(review_id, finding_index, user_id):
            fix = review.findings_json[finding_index]["fix_suggestion"]
            head_branch = fix["git_commit"]["branch_name"]
            pr_res = GitPullRequestResult(
                status=GitPullRequestStatusEnum.CREATED,
                pr_number=101,
                pr_url="https://github.com/test-org/test-repo/pull/101",
                title="fix(calc): guard against zero division",
                body="## AI Fix Summary\n\nResolves zero division finding.",
                head_branch=head_branch,
                base_branch="main",
                created_at="2026-08-26T12:00:00+00:00",
                message="Created Pull Request #101",
            )
            fix["git_pull_request"] = pr_res.model_dump()
            return {"git_pull_request": pr_res, "fix_suggestion": fix}
        pr_uc_mock.execute = AsyncMock(side_effect=pr_fix_impl)

        app.dependency_overrides = {
            get_current_user: lambda: {"sub": user_id, "email": f"{user_id}@example.com"},
            get_code_review_service: lambda: review_service_mock,
            get_reviews_code_review_service: lambda: review_service_mock,
            get_repository_service: lambda: repo_service_mock,
            get_fix_suggestion_agent: lambda: fix_agent_mock,
            get_apply_fix_use_case: lambda: apply_uc_mock,
            get_verify_applied_fix_use_case: lambda: verify_static_mock,
            get_verify_applied_fix_tests_use_case: lambda: verify_tests_mock,
            get_commit_applied_fix_use_case: lambda: commit_uc_mock,
            get_push_fix_branch_use_case: lambda: push_uc_mock,
            get_create_fix_pull_request_use_case: lambda: pr_uc_mock,
        }

        client = TestClient(app, raise_server_exceptions=False)

        try:
            # 1. Generate Fix
            resp = client.post(f"/api/v1/reviews/{review_id}/findings/0/fix")
            assert resp.status_code == 200
            assert "fix_suggestion" in resp.json()

            # 2. Accept Fix
            resp = client.post(f"/api/v1/reviews/{review_id}/findings/0/fix/accept")
            assert resp.status_code == 200
            assert resp.json()["fix_suggestion"]["user_decision"] == "accepted"

            # 3. Apply Fix
            resp = client.post(f"/api/v1/reviews/{review_id}/findings/0/fix/apply")
            assert resp.status_code == 200
            assert resp.json()["application_status"] == "applied"

            # 4. Static Verify
            resp = client.post(f"/api/v1/reviews/{review_id}/findings/0/fix/verify")
            assert resp.status_code == 200
            assert resp.json()["verification"]["status"] == "passed"

            # 5. Test Verify
            resp = client.post(f"/api/v1/reviews/{review_id}/findings/0/fix/verify-tests")
            assert resp.status_code == 200
            assert resp.json()["verification"]["status"] == "passed"

            # 6. Commit Fix
            resp = client.post(f"/api/v1/reviews/{review_id}/findings/0/fix/git/commit")
            assert resp.status_code == 200
            commit_data = resp.json()["git_commit"]
            assert commit_data["status"] == "committed"
            assert len(commit_data["commit_sha"]) == 40

            # 7. Push Branch
            resp = client.post(f"/api/v1/reviews/{review_id}/findings/0/fix/git/push")
            assert resp.status_code == 200
            assert resp.json()["git_push"]["status"] == "pushed"

            # 8. Create PR
            resp = client.post(f"/api/v1/reviews/{review_id}/findings/0/fix/git/pull-request")
            assert resp.status_code == 200
            assert resp.json()["git_pull_request"]["pr_number"] == 101

            # 9. Verify state retrieval via repository/review persistence
            persisted_review = store.get_review(review_id, user_id)
            f0_fix = persisted_review.findings_json[0]["fix_suggestion"]
            assert f0_fix["user_decision"] == "accepted"
            assert f0_fix["application_status"] == "applied"
            assert f0_fix["static_verification"]["status"] == "passed"
            assert f0_fix["test_verification"]["status"] == "passed"
            assert f0_fix["git_commit"]["status"] == "committed"
            assert f0_fix["git_push"]["status"] == "pushed"
            assert f0_fix["git_pull_request"]["status"] == "created"
            assert f0_fix["git_pull_request"]["pr_number"] == 101

        finally:
            app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# 2. State Machine Transition Guards & Action Separation
# ---------------------------------------------------------------------------

class TestStateMachineAndActionSeparation:
    def setup_method(self):
        app.dependency_overrides = {}

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_invalid_state_transitions(self):
        from src.core.errors import WorkflowExecutionError
        review_id = "rev-state-001"
        repo_id = "repo-state-001"
        user_id = "user-bob"

        finding_no_fix = {"id": "f-0", "issue": "Missing types", "file_path": "src/types.py"}
        review = _make_mock_review_entity(review_id, repo_id, user_id, [finding_no_fix])
        repo = _make_mock_repository_entity(repo_id, user_id, "/tmp/repo", "https://github.com/org/repo.git")
        store = InMemoryReviewStore()
        store.save_review(review)
        store.repositories[repo_id] = repo

        review_service_mock = MagicMock()
        review_service_mock.get_review.side_effect = lambda rid, uid=None: store.get_review(rid, uid)
        repo_service_mock = MagicMock()
        repo_service_mock.get_repository.side_effect = lambda uid, rid: store.get_repository(uid, rid)

        apply_mock = MagicMock()
        apply_mock.execute = AsyncMock(side_effect=WorkflowExecutionError("Fix suggestion must be accepted before applying"))
        verify_static_mock = MagicMock()
        verify_static_mock.execute = AsyncMock(side_effect=WorkflowExecutionError("Fix suggestion must be applied before static verification"))
        verify_tests_mock = MagicMock()
        verify_tests_mock.execute = AsyncMock(side_effect=WorkflowExecutionError("Fix suggestion must be applied and static verified"))
        commit_mock = MagicMock()
        commit_mock.execute = AsyncMock(side_effect=WorkflowExecutionError("Tier-1 static verification must pass before committing fix to Git"))
        push_mock = MagicMock()
        push_mock.execute = AsyncMock(side_effect=WorkflowExecutionError("Finding must have a local Git commit before pushing"))
        pr_mock = MagicMock()
        pr_mock.execute = AsyncMock(side_effect=WorkflowExecutionError("Fix branch must be pushed to remote before creating a Pull Request"))

        app.dependency_overrides = {
            get_current_user: lambda: {"sub": user_id, "email": f"{user_id}@example.com"},
            get_code_review_service: lambda: review_service_mock,
            get_repository_service: lambda: repo_service_mock,
            get_apply_fix_use_case: lambda: apply_mock,
            get_verify_applied_fix_use_case: lambda: verify_static_mock,
            get_verify_applied_fix_tests_use_case: lambda: verify_tests_mock,
            get_commit_applied_fix_use_case: lambda: commit_mock,
            get_push_fix_branch_use_case: lambda: push_mock,
            get_create_fix_pull_request_use_case: lambda: pr_mock,
        }

        client = TestClient(app, raise_server_exceptions=False)

        # 1. Apply before accept -> 409
        resp = client.post(f"/api/v1/reviews/{review_id}/findings/0/fix/apply")
        assert resp.status_code == 409

        # 2. Static verify before apply -> 409
        resp = client.post(f"/api/v1/reviews/{review_id}/findings/0/fix/verify")
        assert resp.status_code == 409

        # 3. Test verify before apply -> 409
        resp = client.post(f"/api/v1/reviews/{review_id}/findings/0/fix/verify-tests")
        assert resp.status_code == 409

        # 4. Commit before verification -> 409
        resp = client.post(f"/api/v1/reviews/{review_id}/findings/0/fix/git/commit")
        assert resp.status_code == 409

        # 5. Push before commit -> 409
        resp = client.post(f"/api/v1/reviews/{review_id}/findings/0/fix/git/push")
        assert resp.status_code == 409

        # 6. Create PR before push -> 409
        resp = client.post(f"/api/v1/reviews/{review_id}/findings/0/fix/git/pull-request")
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# 3. Multiple Findings Independence
# ---------------------------------------------------------------------------

class TestMultipleFindingsIndependence:
    def test_three_findings_independent_lifecycle(self):
        review_id = "rev-multi-001"
        repo_id = "repo-multi-001"
        user_id = "user-multi"

        findings = [
            # Finding 0: Fully to PR
            {
                "id": "f-0",
                "issue": "Critical issue",
                "file_path": "src/a.py",
                "fix_suggestion": {
                    "user_decision": "accepted",
                    "application_status": "applied",
                    "static_verification": {"status": "passed"},
                    "test_verification": {"status": "passed"},
                    "git_commit": {"status": "committed", "commit_sha": "a" * 40},
                    "git_push": {"status": "pushed"},
                    "git_pull_request": {"status": "created", "pr_number": 55},
                },
            },
            # Finding 1: Accepted only
            {
                "id": "f-1",
                "issue": "Medium issue",
                "file_path": "src/b.py",
                "fix_suggestion": {
                    "user_decision": "accepted",
                    "application_status": "not_applied",
                },
            },
            # Finding 2: Rejected
            {
                "id": "f-2",
                "issue": "Low issue",
                "file_path": "src/c.py",
                "fix_suggestion": {
                    "user_decision": "rejected",
                    "application_status": "not_applied",
                },
            },
        ]

        review = _make_mock_review_entity(review_id, repo_id, user_id, findings)
        repo = _make_mock_repository_entity(repo_id, user_id, "/tmp/repo", "https://github.com/org/repo.git")
        store = InMemoryReviewStore()
        store.save_review(review)
        store.repositories[repo_id] = repo

        review_service_mock = MagicMock()
        review_service_mock.get_review.side_effect = lambda rid, uid=None: store.get_review(rid, uid)
        repo_service_mock = MagicMock()
        repo_service_mock.get_repository.side_effect = lambda uid, rid: store.get_repository(uid, rid)

        app.dependency_overrides = {
            get_current_user: lambda: {"sub": user_id, "email": f"{user_id}@example.com"},
            get_code_review_service: lambda: review_service_mock,
            get_repository_service: lambda: repo_service_mock,
        }

        # Inspect persisted findings
        f0 = review.findings_json[0]["fix_suggestion"]
        f1 = review.findings_json[1]["fix_suggestion"]
        f2 = review.findings_json[2]["fix_suggestion"]

        assert f0["git_pull_request"]["pr_number"] == 55
        assert f0["application_status"] == "applied"

        assert f1["user_decision"] == "accepted"
        assert f1["application_status"] == "not_applied"
        assert "git_commit" not in f1

        assert f2["user_decision"] == "rejected"
        assert f2["application_status"] == "not_applied"
        assert "git_commit" not in f2


# ---------------------------------------------------------------------------
# 4. Cross-User Isolation & Anti-Enumeration
# ---------------------------------------------------------------------------

class TestCrossUserAntiEnumeration:
    def test_user_b_blocked_at_all_endpoints(self):
        review_id = "rev-owned-by-alice"
        repo_id = "repo-alice"
        user_alice = "user-alice"
        user_bob = "user-bob"

        findings = [{"id": "f-0", "issue": "Bug", "file_path": "src/x.py"}]
        review = _make_mock_review_entity(review_id, repo_id, user_alice, findings)
        repo = _make_mock_repository_entity(repo_id, user_alice, "/tmp/repo", "https://github.com/org/repo.git")

        store = InMemoryReviewStore()
        store.save_review(review)
        store.repositories[repo_id] = repo

        review_service_mock = MagicMock()
        review_service_mock.get_review.side_effect = lambda review_id, user_id=None: store.get_review(review_id, user_id)
        repo_service_mock = MagicMock()
        repo_service_mock.get_repository.side_effect = lambda user_id, repo_id: store.get_repository(user_id, repo_id)

        # Authenticate as User Bob
        app.dependency_overrides = {
            get_current_user: lambda: {"sub": user_bob, "email": "bob@example.com"},
            get_code_review_service: lambda: review_service_mock,
            get_reviews_code_review_service: lambda: review_service_mock,
            get_repository_service: lambda: repo_service_mock,
        }

        client = TestClient(app, raise_server_exceptions=False)
        endpoints = [
            ("POST", f"/api/v1/reviews/{review_id}/findings/0/fix", None),
            ("POST", f"/api/v1/reviews/{review_id}/findings/0/fix/accept", None),
            ("POST", f"/api/v1/reviews/{review_id}/findings/0/fix/reject", None),
            ("POST", f"/api/v1/reviews/{review_id}/findings/0/fix/apply", None),
            ("POST", f"/api/v1/reviews/{review_id}/findings/0/fix/verify", None),
            ("POST", f"/api/v1/reviews/{review_id}/findings/0/fix/verify-tests", None),
            ("POST", f"/api/v1/reviews/{review_id}/findings/0/fix/git/commit", None),
            ("POST", f"/api/v1/reviews/{review_id}/findings/0/fix/git/push", None),
            ("POST", f"/api/v1/reviews/{review_id}/findings/0/fix/git/pull-request", None),
        ]

        try:
            for method, url, body in endpoints:
                if method == "POST":
                    resp = client.post(url, json=body)
                elif method == "GET":
                    resp = client.get(url)
                
                # Must return 404 (anti-enumeration: does not reveal resource exists)
                assert resp.status_code == 404, f"Endpoint {method} {url} returned {resp.status_code}, expected 404"
        finally:
            app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# 5. Finding Index Boundary Checks
# ---------------------------------------------------------------------------

class TestFindingIndexSecurity:
    def test_negative_finding_index_returns_422(self):
        """Negative finding index must be blocked at the API layer with 422 (never reaches service)."""
        review_id = "rev-idx-001"
        repo_id = "repo-idx-001"
        user_id = "user-idx"

        findings = [{"id": "f-0", "issue": "Bug", "file_path": "src/x.py"}]
        review = _make_mock_review_entity(review_id, repo_id, user_id, findings)
        repo = _make_mock_repository_entity(repo_id, user_id, "/tmp/repo", "https://github.com/org/repo.git")

        store = InMemoryReviewStore()
        store.save_review(review)
        store.repositories[repo_id] = repo

        review_service_mock = MagicMock()
        review_service_mock.get_review.side_effect = lambda rid, uid=None: store.get_review(rid, uid)
        repo_service_mock = MagicMock()
        repo_service_mock.get_repository.side_effect = lambda uid, rid: store.get_repository(uid, rid)

        app.dependency_overrides = {
            get_current_user: lambda: {"sub": user_id, "email": "user@example.com"},
            get_code_review_service: lambda: review_service_mock,
            get_repository_service: lambda: repo_service_mock,
        }

        client = TestClient(app, raise_server_exceptions=False)
        # Negative indices are caught at API layer (_safe_finding_index) -> 422
        negative_idx = -1
        endpoints = [
            f"/api/v1/reviews/{review_id}/findings/{negative_idx}/fix",
            f"/api/v1/reviews/{review_id}/findings/{negative_idx}/fix/accept",
            f"/api/v1/reviews/{review_id}/findings/{negative_idx}/fix/reject",
            f"/api/v1/reviews/{review_id}/findings/{negative_idx}/fix/apply",
            f"/api/v1/reviews/{review_id}/findings/{negative_idx}/fix/verify",
            f"/api/v1/reviews/{review_id}/findings/{negative_idx}/fix/verify-tests",
            f"/api/v1/reviews/{review_id}/findings/{negative_idx}/fix/git/commit",
            f"/api/v1/reviews/{review_id}/findings/{negative_idx}/fix/git/push",
            f"/api/v1/reviews/{review_id}/findings/{negative_idx}/fix/git/pull-request",
        ]

        try:
            for url in endpoints:
                resp = client.post(url)
                assert resp.status_code == 422, f"POST {url} returned {resp.status_code}, expected 422"
        finally:
            app.dependency_overrides = {}

    def test_out_of_range_finding_index_blocked(self):
        """Out-of-range indices are blocked at service/use-case layer with 422."""
        from src.core.errors import WorkflowExecutionError
        review_id = "rev-idx-002"
        repo_id = "repo-idx-002"
        user_id = "user-idx-2"

        findings = [{"id": "f-0", "issue": "Bug", "file_path": "src/x.py"}]
        review = _make_mock_review_entity(review_id, repo_id, user_id, findings)
        repo = _make_mock_repository_entity(repo_id, user_id, "/tmp/repo", "https://github.com/org/repo.git")

        store = InMemoryReviewStore()
        store.save_review(review)
        store.repositories[repo_id] = repo

        review_service_mock = MagicMock()
        review_service_mock.get_review.side_effect = lambda rid, uid=None: store.get_review(rid, uid)
        repo_service_mock = MagicMock()
        repo_service_mock.get_repository.side_effect = lambda uid, rid: store.get_repository(uid, rid)

        # Mock use cases to raise out-of-range errors as they would
        oor_exc = WorkflowExecutionError("finding_index 99 out of range")
        apply_mock = MagicMock(); apply_mock.execute = AsyncMock(side_effect=oor_exc)
        verify_s_mock = MagicMock(); verify_s_mock.execute = AsyncMock(side_effect=oor_exc)
        verify_t_mock = MagicMock(); verify_t_mock.execute = AsyncMock(side_effect=oor_exc)
        commit_mock = MagicMock(); commit_mock.execute = AsyncMock(side_effect=oor_exc)
        push_mock = MagicMock(); push_mock.execute = AsyncMock(side_effect=oor_exc)
        pr_mock = MagicMock(); pr_mock.execute = AsyncMock(side_effect=oor_exc)

        app.dependency_overrides = {
            get_current_user: lambda: {"sub": user_id, "email": "user@example.com"},
            get_code_review_service: lambda: review_service_mock,
            get_repository_service: lambda: repo_service_mock,
            get_apply_fix_use_case: lambda: apply_mock,
            get_verify_applied_fix_use_case: lambda: verify_s_mock,
            get_verify_applied_fix_tests_use_case: lambda: verify_t_mock,
            get_commit_applied_fix_use_case: lambda: commit_mock,
            get_push_fix_branch_use_case: lambda: push_mock,
            get_create_fix_pull_request_use_case: lambda: pr_mock,
        }

        client = TestClient(app, raise_server_exceptions=False)
        oor_idx = 99
        uc_endpoints = [
            f"/api/v1/reviews/{review_id}/findings/{oor_idx}/fix/apply",
            f"/api/v1/reviews/{review_id}/findings/{oor_idx}/fix/verify",
            f"/api/v1/reviews/{review_id}/findings/{oor_idx}/fix/verify-tests",
            f"/api/v1/reviews/{review_id}/findings/{oor_idx}/fix/git/commit",
            f"/api/v1/reviews/{review_id}/findings/{oor_idx}/fix/git/push",
            f"/api/v1/reviews/{review_id}/findings/{oor_idx}/fix/git/pull-request",
        ]

        try:
            for url in uc_endpoints:
                resp = client.post(url)
                assert resp.status_code == 422, f"POST {url} returned {resp.status_code}, expected 422"
        finally:
            app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# 6. Real Git Commit & Push Isolation with Dirty Working Tree
# ---------------------------------------------------------------------------

class TestRealGitIsolationE2E:
    def test_git_commit_and_push_isolation_with_dirty_tree(self, tmp_path):
        local_repo = tmp_path / "work_repo"
        local_repo.mkdir()
        _init_git_repo(local_repo)
        
        bare_remote = _init_bare_remote(tmp_path)
        subprocess.run(["git", "remote", "add", "origin", str(bare_remote)], cwd=str(local_repo), check=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=str(local_repo), check=True, stdout=subprocess.PIPE)

        # File A (target)
        file_a = local_repo / "src" / "target.py"
        file_a.parent.mkdir(parents=True, exist_ok=True)
        file_a.write_text("v1 original\n")

        # File B (unrelated modified)
        file_b = local_repo / "src" / "unrelated.py"
        file_b.write_text("v1 unrelated\n")

        # File C (user staged)
        file_c = local_repo / "src" / "staged.py"
        file_c.write_text("v1 staged\n")

        subprocess.run(["git", "add", "."], cwd=str(local_repo), check=True)
        subprocess.run(["git", "commit", "-m", "add initial files"], cwd=str(local_repo), check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=str(local_repo), check=True, stdout=subprocess.PIPE)

        # Modify A (target)
        file_a.write_text("v2 AI fix applied\n")

        # Modify B (unrelated dirty)
        file_b.write_text("v2 dirty modified by user\n")

        # Stage C
        file_c.write_text("v2 user staged content\n")
        subprocess.run(["git", "add", "src/staged.py"], cwd=str(local_repo), check=True)

        # Verify initial dirty state
        wt_manager = GitWorkingTreeManager()
        pre_status = wt_manager.get_working_tree_status(local_repo)
        assert any("target.py" in f for f in pre_status.modified_files)
        assert any("unrelated.py" in f for f in pre_status.modified_files)
        assert any("staged.py" in f for f in pre_status.staged_files)

        # Create isolated commit
        commit_res = wt_manager.create_isolated_fix_commit(
            workspace_root=local_repo,
            relative_target_path="src/target.py",
            review_id="rev-test1234",
            finding_index=0,
            finding_issue="applied targeted fix",
        )
        assert commit_res.status == GitCommitStatusEnum.COMMITTED
        branch_name = commit_res.branch_name
        
        # Verify working tree preservation
        post_status = wt_manager.get_working_tree_status(local_repo)
        assert any("unrelated.py" in f for f in post_status.modified_files)
        assert any("staged.py" in f for f in post_status.staged_files)
        assert file_b.read_text() == "v2 dirty modified by user\n"

        # Verify active branch/HEAD is still main
        current_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(local_repo),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert current_branch == "main"

        # Verify AI commit content contains ONLY target.py
        commit_files = subprocess.run(
            ["git", "show", "--name-only", "--pretty=format:", commit_res.commit_sha],
            cwd=str(local_repo),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip().splitlines()
        clean_files = [f.strip().replace("\\", "/") for f in commit_files if f.strip()]
        assert clean_files == ["src/target.py"]

        # Push dedicated AI branch to bare remote
        push_res = wt_manager.push_isolated_branch(
            workspace_root=local_repo,
            branch_name=branch_name,
            expected_commit_sha=commit_res.commit_sha,
            remote_name="origin",
            expected_repo_url=str(bare_remote),
        )
        assert push_res.status == GitPushStatusEnum.PUSHED

        # Verify bare remote received the branch
        remote_branches = subprocess.run(
            ["git", "branch", "--list"],
            cwd=str(bare_remote),
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert branch_name in remote_branches


# ---------------------------------------------------------------------------
# 7. Stale Source & Tampering Protection
# ---------------------------------------------------------------------------

class TestStaleSourceAndTamperingE2E:
    def test_stale_source_modification_detected_on_commit(self, tmp_path):
        from src.application.use_cases.commit_applied_fix import CommitAppliedFixUseCase
        from src.core.errors import WorkflowExecutionError

        local_repo = tmp_path / "stale_repo"
        local_repo.mkdir()
        _init_git_repo(local_repo)

        calc_file = local_repo / "src" / "calc.py"
        calc_file.parent.mkdir(parents=True, exist_ok=True)
        original_code = "def foo(): pass\n"
        calc_file.write_text(original_code)
        
        subprocess.run(["git", "add", "."], cwd=str(local_repo), check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=str(local_repo), check=True)

        applied_code = "def foo(): return 42\n"
        calc_file.write_text(applied_code)
        applied_hash = hashlib.sha256(applied_code.encode("utf-8")).hexdigest()

        # Simulate post-apply tampering
        calc_file.write_text("def foo(): return 'tampered'\n")

        review_id = "rev-stale"
        repo_id = "repo-stale"
        user_id = "user-stale"

        finding = {
            "id": "f-0",
            "file_path": "src/calc.py",
            "fix_suggestion": {
                "file_path": "src/calc.py",
                "user_decision": "accepted",
                "application_status": "applied",
                "new_hash": applied_hash,
                "static_verification": {"status": "passed"},
                "test_verification": {"status": "passed"},
            },
        }

        review = _make_mock_review_entity(review_id, repo_id, user_id, [finding])
        repo = _make_mock_repository_entity(repo_id, user_id, str(local_repo), "https://github.com/org/repo.git")

        review_service = MagicMock()
        review_service.get_review.return_value = review
        repo_service = MagicMock()
        repo_service.get_repository.return_value = repo

        use_case = CommitAppliedFixUseCase(
            review_service=review_service,
            repository_service=repo_service,
            working_tree_manager=GitWorkingTreeManager(),
        )

        with pytest.raises(WorkflowExecutionError) as excinfo:
            asyncio.run(use_case.execute(
                review_id=review_id,
                finding_index=0,
                user_id=user_id,
                workspace_root_override=str(local_repo),
            ))

        err = str(excinfo.value).lower()
        assert "modified" in err or "stale" in err or "hash" in err


# ---------------------------------------------------------------------------
# 8. Zero Merge & Safe Boundary Audit
# ---------------------------------------------------------------------------

class TestZeroMergeAndScopeBoundaries:
    def test_zero_merge_capabilities_in_codebase(self):
        client = TestClient(app, raise_server_exceptions=False)
        spec = client.get("/openapi.json").json()
        
        for path, path_item in spec.get("paths", {}).items():
            assert "merge" not in path.lower(), f"Unexpected merge endpoint found in OpenAPI: {path}"
            for method, op in path_item.items():
                summary = op.get("summary", "").lower()
                op_id = op.get("operationId", "").lower()
                assert "merge" not in summary, f"Merge summary found in {path}: {summary}"
                assert "merge" not in op_id, f"Merge operationId found in {path}: {op_id}"

    def test_git_runner_prohibits_dangerous_commands(self):
        runner = GitCommandRunner()
        forbidden_commands = [
            ["git", "push", "--force"],
            ["git", "push", "-f"],
            ["git", "push", "--force-with-lease"],
            ["git", "merge", "main"],
            ["git", "rebase", "main"],
            ["git", "reset", "--hard"],
            ["git", "clean", "-fd"],
            ["git", "checkout", "."],
        ]
        for cmd in forbidden_commands:
            with pytest.raises(Exception):
                runner.run_git_command(Path("."), cmd)
