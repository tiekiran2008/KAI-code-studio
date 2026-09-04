"""
Security Tests: Cross-User GitHub Integration Isolation
========================================================
Tests proving:
1. User A GitHub token is used for User A.
2. User B GitHub token is used for User B.
3. User B cannot access User A's GitHub integration.
4. Disconnected user cannot perform authenticated GitHub operations.
5. Missing GitHub integration produces a safe application error (not a crash).
6. Decryption/token retrieval remains backend-only.
7. GitHubToolAdapter does not expose tokens in ToolResult.
8. GitHubPullRequestService does not expose tokens.
9. Logs/errors do not contain token values.
"""
import asyncio
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.persistence.base import Base
from src.infrastructure.persistence.github_models import DBGitHubIntegration
from src.application.services.github_integration_service import GitHubIntegrationService
from src.infrastructure.security.token_encryptor import TokenEncryptor
from src.infrastructure.tools.adapters.github import GitHubToolAdapter
from src.infrastructure.git.github_pr_service import GitHubPullRequestService


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
    return TokenEncryptor(key="cross-user-test-static-key-32b!!!")


@pytest.fixture()
def user_a_id():
    return str(uuid.uuid4())


@pytest.fixture()
def user_b_id():
    return str(uuid.uuid4())


TOKEN_A = "gho_user_a_oauth_token_unique_12345"
TOKEN_B = "gho_user_b_oauth_token_unique_67890"


def _create_integration(db_session, encryptor, user_id: str, raw_token: str, username: str):
    """Helper to insert an integration record for a user."""
    record = DBGitHubIntegration(
        id=str(uuid.uuid4()),
        user_id=user_id,
        github_user_id=str(abs(hash(user_id)) % 100000),
        github_username=username,
        avatar_url=f"https://avatars.github.com/u/test",
        access_token_encrypted=encryptor.encrypt(raw_token),
        token_type="bearer",
        scope="repo,read:user",
        connected_at=datetime.now(timezone.utc),
    )
    db_session.add(record)
    db_session.commit()
    return record


# ─── Test 1 & 2: Per-user token isolation ─────────────────────────────────────

class TestPerUserTokenResolution:
    def test_user_a_receives_user_a_token(self, db_session, encryptor, user_a_id, user_b_id):
        """Token resolved for User A must equal TOKEN_A and not TOKEN_B."""
        _create_integration(db_session, encryptor, user_a_id, TOKEN_A, "user-a")
        _create_integration(db_session, encryptor, user_b_id, TOKEN_B, "user-b")

        GitHubIntegrationService._state_cache.clear()
        svc = GitHubIntegrationService(db_session=db_session, encryptor=encryptor)

        resolved = svc.get_decrypted_token(user_a_id)
        assert resolved == TOKEN_A, "User A should receive their own token"
        assert resolved != TOKEN_B, "User A must never receive User B's token"

    def test_user_b_receives_user_b_token(self, db_session, encryptor, user_a_id, user_b_id):
        """Token resolved for User B must equal TOKEN_B and not TOKEN_A."""
        _create_integration(db_session, encryptor, user_a_id, TOKEN_A, "user-a")
        _create_integration(db_session, encryptor, user_b_id, TOKEN_B, "user-b")

        svc = GitHubIntegrationService(db_session=db_session, encryptor=encryptor)

        resolved = svc.get_decrypted_token(user_b_id)
        assert resolved == TOKEN_B, "User B should receive their own token"
        assert resolved != TOKEN_A, "User B must never receive User A's token"


# ─── Test 3: Cross-user access denial ─────────────────────────────────────────

class TestCrossUserAccessDenial:
    def test_user_b_cannot_access_user_a_integration(self, db_session, encryptor, user_a_id, user_b_id):
        """User B's status check must return not-connected, not User A's data."""
        _create_integration(db_session, encryptor, user_a_id, TOKEN_A, "user-a")
        # User B has NO integration record

        svc = GitHubIntegrationService(db_session=db_session, encryptor=encryptor)

        # User B queries their own status — must show disconnected
        status_b = svc.get_status(user_b_id)
        assert status_b["connected"] is False
        assert status_b["username"] is None

    def test_user_b_token_is_none_without_integration(self, db_session, encryptor, user_a_id, user_b_id):
        """User B must get None token when they have no GitHub integration."""
        _create_integration(db_session, encryptor, user_a_id, TOKEN_A, "user-a")

        svc = GitHubIntegrationService(db_session=db_session, encryptor=encryptor)
        token_b = svc.get_decrypted_token(user_b_id)
        assert token_b is None


# ─── Test 4: Disconnected user cannot perform operations ─────────────────────

class TestDisconnectedUserOperations:
    @pytest.mark.asyncio
    async def test_list_repositories_raises_for_disconnected_user(self, db_session, encryptor, user_a_id):
        """list_user_repositories must raise ValueError for unconnected user."""
        svc = GitHubIntegrationService(db_session=db_session, encryptor=encryptor)
        with pytest.raises(ValueError, match="not connected"):
            await svc.list_user_repositories(user_a_id)

    def test_get_decrypted_token_returns_none_for_disconnected(self, db_session, encryptor, user_a_id):
        svc = GitHubIntegrationService(db_session=db_session, encryptor=encryptor)
        assert svc.get_decrypted_token(user_a_id) is None


# ─── Test 5: Missing integration produces a safe error ────────────────────────

class TestMissingIntegrationSafeError:
    @pytest.mark.asyncio
    async def test_tool_adapter_returns_graceful_error_when_no_token(self):
        """GitHubToolAdapter must return ToolResult(success=False) without crashing."""
        adapter = GitHubToolAdapter(token_resolver=lambda: None)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = ""
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await adapter.execute(owner="acme", repo="secret", action="branches")

        assert result.success is False
        assert result.error is not None


# ─── Test 6: Token retrieval is backend-only ──────────────────────────────────

class TestBackendOnlyTokenRetrieval:
    def test_status_response_does_not_contain_token(self, db_session, encryptor, user_a_id):
        """get_status() must never include a token value in its response dict."""
        _create_integration(db_session, encryptor, user_a_id, TOKEN_A, "user-a")
        svc = GitHubIntegrationService(db_session=db_session, encryptor=encryptor)

        status = svc.get_status(user_a_id)
        status_str = str(status)

        # Raw token must not appear in status dict
        assert TOKEN_A not in status_str
        # Encrypted blob must not appear in status dict
        assert "access_token" not in status_str
        assert "token" not in status_str.lower().replace("connected_at", "")

    def test_get_decrypted_token_is_not_in_status_response(self, db_session, encryptor, user_a_id):
        """get_decrypted_token() is intentionally internal; result is not in status."""
        _create_integration(db_session, encryptor, user_a_id, TOKEN_A, "user-a")
        svc = GitHubIntegrationService(db_session=db_session, encryptor=encryptor)

        token = svc.get_decrypted_token(user_a_id)
        status = svc.get_status(user_a_id)

        assert token == TOKEN_A  # correct resolved value
        assert token not in str(status)  # not leaked into status


# ─── Test 7: GitHubToolAdapter does not expose tokens ─────────────────────────

class TestGitHubToolAdapterTokenSafety:
    @pytest.mark.asyncio
    async def test_tool_result_does_not_expose_token_on_success(self):
        """Successful ToolResult.data must not contain the token value."""
        SECRET_TOKEN = "gho_shouldnotappearinresult"
        adapter = GitHubToolAdapter(github_token=SECRET_TOKEN)

        mock_json_data = [{"name": "main"}, {"name": "develop"}]

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value=mock_json_data)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await adapter.execute(owner="acme", repo="public-repo", action="branches")

        assert result.success is True
        assert SECRET_TOKEN not in str(result.data)

    @pytest.mark.asyncio
    async def test_tool_result_error_does_not_expose_token(self):
        """ToolResult.error on failure must not contain the token value."""
        SECRET_TOKEN = "gho_shouldnotappearinerror"
        adapter = GitHubToolAdapter(github_token=SECRET_TOKEN)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.text = "Forbidden"
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await adapter.execute(owner="acme", repo="private-repo", action="branches")

        assert result.success is False
        assert SECRET_TOKEN not in str(result.error)

    def test_token_resolver_not_stored_as_plaintext(self):
        """GitHubToolAdapter must not store the resolved token as a public attribute."""
        SECRET_TOKEN = "gho_resolvershouldbeclosure"
        adapter = GitHubToolAdapter(token_resolver=lambda: SECRET_TOKEN)

        # The raw token must not appear in __dict__
        all_attrs = str(adapter.__dict__)
        assert SECRET_TOKEN not in all_attrs


# ─── Test 8: GitHubPullRequestService does not expose tokens ──────────────────

class TestPullRequestServiceTokenSafety:
    @pytest.mark.asyncio
    async def test_pr_error_message_masks_token(self):
        """GitHubPullRequestService._mask_error must redact token patterns."""
        svc = GitHubPullRequestService()
        raw_error = f"Authorization: Bearer ghp_supersecrettoken1234567890123456 failed"
        masked = svc._mask_error(raw_error)
        assert "ghp_supersecrettoken1234567890123456" not in masked
        assert "[REDACTED_TOKEN]" in masked

    @pytest.mark.asyncio
    async def test_pr_result_does_not_include_token(self):
        """GitPullRequestResult returned by create_pull_request must not contain token."""
        SECRET_TOKEN = "gho_prservicetokentestvalue"
        svc = GitHubPullRequestService()

        mock_response_find = MagicMock()
        mock_response_find.status_code = 200
        mock_response_find.json = MagicMock(return_value=[])

        mock_response_create = MagicMock()
        mock_response_create.status_code = 201
        mock_response_create.json = MagicMock(return_value={
            "number": 42,
            "html_url": "https://github.com/acme/repo/pull/42",
            "created_at": "2026-09-04T00:00:00Z",
        })

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response_find)
            mock_client.post = AsyncMock(return_value=mock_response_create)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await svc.create_pull_request(
                owner="acme",
                repo="repo",
                head_branch="fix/issue-1",
                base_branch="main",
                title="fix: test issue",
                body="Test body",
                token=SECRET_TOKEN,
            )

        result_str = str(result)
        assert SECRET_TOKEN not in result_str


# ─── Test 9: Logs do not contain token values ────────────────────────────────

class TestLogTokenSafety:
    def test_github_integration_service_logs_no_token(self, db_session, encryptor, user_a_id, caplog):
        """GitHubIntegrationService operations must not log raw token values."""
        import logging
        _create_integration(db_session, encryptor, user_a_id, TOKEN_A, "user-a")

        svc = GitHubIntegrationService(db_session=db_session, encryptor=encryptor)

        with caplog.at_level(logging.DEBUG):
            _ = svc.get_status(user_a_id)
            _ = svc.get_decrypted_token(user_a_id)

        for record in caplog.records:
            assert TOKEN_A not in record.getMessage(), (
                f"Raw token found in log message: {record.getMessage()}"
            )

    @pytest.mark.asyncio
    async def test_tool_adapter_logs_no_token(self, caplog):
        """GitHubToolAdapter must not log the token in any log record."""
        import logging
        SECRET_TOKEN = "gho_tooladaptertokentestvalue"
        adapter = GitHubToolAdapter(github_token=SECRET_TOKEN)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with caplog.at_level(logging.DEBUG):
                await adapter.execute(owner="acme", repo="missing", action="branches")

        for record in caplog.records:
            assert SECRET_TOKEN not in record.getMessage()
