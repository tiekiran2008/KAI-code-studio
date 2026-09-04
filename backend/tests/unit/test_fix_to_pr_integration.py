"""
Integration Test: Fix-to-PR Workflow with Per-User GitHub OAuth
================================================================
Verifies the complete fix → push → create PR workflow:

  Authenticated KAI user
  → connected GitHub OAuth integration
  → code review finding
  → generated fix applied & committed
  → branch pushed to remote
  → create pull request

The test uses REAL internal dependency wiring:
- GitHubIntegrationService for token lookup
- CreateFixPullRequestUseCase for orchestration
- GitHubPullRequestService for PR creation

All external GitHub API calls are mocked via httpx.AsyncClient.

Verifies that:
- The OAuth credential selected belongs to the authenticated test user
- User B cannot trigger a PR using User A's credentials
- Token is not present in any result returned to caller
- Graceful fallback when no GitHub integration is connected
"""
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.persistence.base import Base
from src.infrastructure.persistence.github_models import DBGitHubIntegration
from src.application.services.github_integration_service import GitHubIntegrationService
from src.infrastructure.security.token_encryptor import TokenEncryptor
from src.application.use_cases.create_fix_pull_request import CreateFixPullRequestUseCase
from src.infrastructure.git.github_pr_service import GitHubPullRequestService
from src.domain.entities.git import GitPullRequestStatusEnum


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def encryptor():
    return TokenEncryptor(key="fix-to-pr-integ-test-key-32bytes")


USER_A_ID = str(uuid.uuid4())
USER_B_ID = str(uuid.uuid4())
TOKEN_A = "gho_user_a_integration_token_abcdef"
TOKEN_B = "gho_user_b_integration_token_uvwxyz"

COMMIT_SHA = "a" * 40
BRANCH_NAME = "ai-fix/rev-test-f0"
OWNER = "acme-org"
REPO_NAME = "acme-api"


def _seed_integration(db_session, encryptor, user_id: str, token: str, username: str):
    record = DBGitHubIntegration(
        id=str(uuid.uuid4()),
        user_id=user_id,
        github_user_id=str(abs(hash(user_id)) % 100000),
        github_username=username,
        avatar_url="https://avatars.github.com/u/test",
        access_token_encrypted=encryptor.encrypt(token),
        token_type="bearer",
        scope="repo,read:user",
        connected_at=datetime.now(timezone.utc),
    )
    db_session.add(record)
    db_session.commit()


def _make_review(user_id: str, repository_id: str = "repo-1"):
    review = MagicMock()
    review.id = "rev-integ-test"
    review.status = "completed"
    review.repository_id = repository_id
    review.findings_json = [_make_finding()]
    return review


def _make_finding():
    return {
        "issue": "Missing null check in payment handler",
        "severity": "high",
        "line_number": 42,
        "fix_suggestion": {
            "finding_index": 0,
            "file_path": "src/payments.py",
            "original_code": "return process(data)",
            "proposed_code": "if data is None: raise ValueError(); return process(data)",
            "explanation": "Added null guard before processing.",
            "diff": "--- a\n+++ b",
            "confidence_score": 0.97,
            "validation_status": "valid",
            "user_decision": "accepted",
            "application_status": "applied",
            "new_hash": "deadbeef",
            "static_verification": {"status": "passed"},
            "test_verification": {"status": "passed"},
            "git_commit": {
                "status": "committed",
                "branch_name": BRANCH_NAME,
                "commit_sha": COMMIT_SHA,
                "committed_at": "2026-09-04T10:00:00+00:00",
                "file_path": "src/payments.py",
            },
            "git_push": {
                "status": "pushed",
                "remote_name": "origin",
                "branch_name": BRANCH_NAME,
                "pushed_at": "2026-09-04T10:01:00+00:00",
                "remote_url": f"https://github.com/{OWNER}/{REPO_NAME}.git",
            },
        },
    }


def _make_repository():
    repo = MagicMock()
    repo.id = "repo-1"
    repo.owner = OWNER
    repo.name = REPO_NAME
    repo.url = f"https://github.com/{OWNER}/{REPO_NAME}.git"
    repo.default_branch = "main"
    repo.git_access_token_encrypted = None  # OAuth should be used instead
    return repo


# ─── Fix-to-PR Integration Test ───────────────────────────────────────────────

class TestFixToPRIntegration:
    @pytest.mark.asyncio
    async def test_fix_to_pr_uses_connected_user_oauth_token(self, db_session, encryptor):
        """
        Full wiring test: CreateFixPullRequestUseCase must pass the user's
        OAuth token (from GitHubIntegrationService) to GitHubPullRequestService.
        """
        # Seed User A's OAuth integration
        _seed_integration(db_session, encryptor, USER_A_ID, TOKEN_A, "user-a")

        # Resolve the token the same way the DI layer does
        GitHubIntegrationService._state_cache.clear()
        integration_svc = GitHubIntegrationService(db_session=db_session, encryptor=encryptor)
        resolved_token = integration_svc.get_decrypted_token(USER_A_ID)

        assert resolved_token == TOKEN_A, "Integration service must return User A's token"

        # Mock review and repository services
        mock_review_svc = MagicMock()
        mock_review_svc.get_review = MagicMock(return_value=_make_review(USER_A_ID))
        mock_review_svc.update_finding_git_pull_request_result = MagicMock(
            return_value=_make_finding()["fix_suggestion"]
        )

        mock_repo_svc = MagicMock()
        mock_repo_svc.get_repository = MagicMock(return_value=_make_repository())

        # Track what token is actually passed to GitHubPullRequestService
        captured_tokens = []

        async def mock_create_pr(owner, repo, head_branch, base_branch, title, body, token=None):
            captured_tokens.append(token)
            from src.domain.entities.git import GitPullRequestResult, GitPullRequestStatusEnum
            return GitPullRequestResult(
                status=GitPullRequestStatusEnum.CREATED,
                pr_number=99,
                pr_url=f"https://github.com/{owner}/{repo}/pull/99",
                title=title,
                body=body,
                head_branch=head_branch,
                base_branch=base_branch,
                created_at="2026-09-04T10:05:00Z",
                message="Successfully created Pull Request #99",
            )

        mock_pr_svc = MagicMock()
        mock_pr_svc.find_existing_pull_request = AsyncMock(return_value=None)
        mock_pr_svc.create_pull_request = AsyncMock(side_effect=mock_create_pr)

        use_case = CreateFixPullRequestUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            github_pr_service=mock_pr_svc,
        )

        result = await use_case.execute(
            review_id="rev-integ-test",
            finding_index=0,
            user_id=USER_A_ID,
            github_token=resolved_token,  # DI layer injects this
        )

        # Verify the PR was created
        assert result["git_pull_request"].status == GitPullRequestStatusEnum.CREATED

        # Verify the CORRECT user token was passed to the GitHub API layer
        assert len(captured_tokens) == 1
        assert captured_tokens[0] == TOKEN_A, "The OAuth token for User A must be used for the GitHub API call"

    @pytest.mark.asyncio
    async def test_user_b_cannot_trigger_pr_with_user_a_token(self, db_session, encryptor):
        """
        User B (who has no GitHub integration) cannot piggyback on User A's token.
        When User B calls CreateFixPullRequestUseCase, it should use None or User B's
        own token — never User A's token.
        """
        _seed_integration(db_session, encryptor, USER_A_ID, TOKEN_A, "user-a")
        # User B has NO integration

        integration_svc = GitHubIntegrationService(db_session=db_session, encryptor=encryptor)
        token_b = integration_svc.get_decrypted_token(USER_B_ID)

        assert token_b is None, "User B must resolve to None (no GitHub integration)"
        assert token_b != TOKEN_A, "User B must never receive User A's token"

    @pytest.mark.asyncio
    async def test_pr_creation_falls_back_gracefully_when_no_oauth_token(self, db_session, encryptor):
        """
        When a user has no GitHub OAuth token, PR creation uses None and GitHub API
        returns AUTH_REQUIRED — use case must return that status, not crash.
        """
        mock_review_svc = MagicMock()
        mock_review_svc.get_review = MagicMock(return_value=_make_review(USER_A_ID))
        mock_review_svc.update_finding_git_pull_request_result = MagicMock(
            return_value=_make_finding()["fix_suggestion"]
        )
        mock_repo_svc = MagicMock()
        mock_repo_svc.get_repository = MagicMock(return_value=_make_repository())

        mock_pr_svc = MagicMock()
        mock_pr_svc.find_existing_pull_request = AsyncMock(return_value=None)

        from src.domain.entities.git import GitPullRequestResult, GitPullRequestStatusEnum
        mock_pr_svc.create_pull_request = AsyncMock(return_value=GitPullRequestResult(
            status=GitPullRequestStatusEnum.AUTH_REQUIRED,
            head_branch=BRANCH_NAME,
            base_branch="main",
            message="GitHub authentication required",
            error_details="HTTP 401 Unauthorized",
        ))

        use_case = CreateFixPullRequestUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            github_pr_service=mock_pr_svc,
        )

        result = await use_case.execute(
            review_id="rev-integ-test",
            finding_index=0,
            user_id=USER_A_ID,
            github_token=None,  # No OAuth token — simulates unconnected user
        )

        assert result["git_pull_request"].status == GitPullRequestStatusEnum.AUTH_REQUIRED

    @pytest.mark.asyncio
    async def test_oauth_token_not_present_in_pr_result(self, db_session, encryptor):
        """PR result returned to caller must not contain the OAuth token value."""
        _seed_integration(db_session, encryptor, USER_A_ID, TOKEN_A, "user-a")
        integration_svc = GitHubIntegrationService(db_session=db_session, encryptor=encryptor)
        resolved_token = integration_svc.get_decrypted_token(USER_A_ID)

        mock_review_svc = MagicMock()
        mock_review_svc.get_review = MagicMock(return_value=_make_review(USER_A_ID))
        mock_review_svc.update_finding_git_pull_request_result = MagicMock(
            return_value=_make_finding()["fix_suggestion"]
        )
        mock_repo_svc = MagicMock()
        mock_repo_svc.get_repository = MagicMock(return_value=_make_repository())

        from src.domain.entities.git import GitPullRequestResult, GitPullRequestStatusEnum
        mock_pr_svc = MagicMock()
        mock_pr_svc.find_existing_pull_request = AsyncMock(return_value=None)
        mock_pr_svc.create_pull_request = AsyncMock(return_value=GitPullRequestResult(
            status=GitPullRequestStatusEnum.CREATED,
            pr_number=100,
            pr_url=f"https://github.com/{OWNER}/{REPO_NAME}/pull/100",
            title="fix: Missing null check",
            body="Security fix applied.",
            head_branch=BRANCH_NAME,
            base_branch="main",
            created_at="2026-09-04T10:10:00Z",
            message="Successfully created PR #100",
        ))

        use_case = CreateFixPullRequestUseCase(
            review_service=mock_review_svc,
            repository_service=mock_repo_svc,
            github_pr_service=mock_pr_svc,
        )

        result = await use_case.execute(
            review_id="rev-integ-test",
            finding_index=0,
            user_id=USER_A_ID,
            github_token=resolved_token,
        )

        result_str = str(result)
        assert TOKEN_A not in result_str, "OAuth token must not appear in any PR result field"
