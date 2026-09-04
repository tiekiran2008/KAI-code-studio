"""
Unit Tests: GitHubIntegrationService
======================================
Tests the OAuth state management, token operations, and status/disconnect flows
using an in-memory SQLite database. External HTTP calls are mocked.
"""
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.persistence.base import Base
from src.infrastructure.persistence.github_models import DBGitHubIntegration
from src.application.services.github_integration_service import GitHubIntegrationService
from src.infrastructure.security.token_encryptor import TokenEncryptor


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    """Provide an in-memory SQLite session for each test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def encryptor():
    return TokenEncryptor(key="unit-test-static-key-32bytes!!!!")


@pytest.fixture()
def service(db_session, encryptor):
    # Clear in-memory state cache between tests
    GitHubIntegrationService._state_cache.clear()
    return GitHubIntegrationService(db_session=db_session, encryptor=encryptor)


FAKE_USER_ID = str(uuid.uuid4())


# ─── OAuth State Tests ─────────────────────────────────────────────────────────

class TestOAuthState:
    def test_get_authorization_url_contains_state(self, service):
        url = service.get_authorization_url(FAKE_USER_ID)
        assert "state=" in url
        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "scope=" in url

    def test_validate_state_returns_user_id(self, service):
        url = service.get_authorization_url(FAKE_USER_ID)
        # Extract state from URL
        state = dict(part.split("=", 1) for part in url.split("?", 1)[1].split("&"))["state"]
        result = service.validate_state(state)
        assert result == FAKE_USER_ID

    def test_validate_state_consumed_only_once(self, service):
        url = service.get_authorization_url(FAKE_USER_ID)
        state = dict(part.split("=", 1) for part in url.split("?", 1)[1].split("&"))["state"]
        assert service.validate_state(state) == FAKE_USER_ID
        # Second call must return None (state consumed)
        assert service.validate_state(state) is None

    def test_validate_invalid_state_returns_none(self, service):
        assert service.validate_state("totally-bogus-state") is None

    def test_validate_expired_state_returns_none(self, service):
        import time
        url = service.get_authorization_url(FAKE_USER_ID)
        state = dict(part.split("=", 1) for part in url.split("?", 1)[1].split("&"))["state"]
        # Manually backdate the cached timestamp to simulate expiry
        GitHubIntegrationService._state_cache[state] = (FAKE_USER_ID, time.time() - 700)
        assert service.validate_state(state) is None


# ─── Token Exchange & Connection Tests ────────────────────────────────────────

class TestConnectUserGitHub:
    @pytest.mark.asyncio
    async def test_connect_creates_integration_record(self, service, db_session):
        mock_token_data = {
            "access_token": "gho_fakeoauthtoken1234567890",
            "token_type": "bearer",
            "scope": "repo,read:user,user:email",
        }
        mock_profile = {
            "id": 99999,
            "login": "testuser",
            "avatar_url": "https://avatars.githubusercontent.com/u/99999",
        }

        with patch.object(service, "exchange_code_for_token", new=AsyncMock(return_value=mock_token_data)), \
             patch.object(service, "fetch_github_profile", new=AsyncMock(return_value=mock_profile)):
            record = await service.connect_user_github(FAKE_USER_ID, "fake_code")

        assert record.user_id == FAKE_USER_ID
        assert record.github_username == "testuser"
        assert record.access_token_encrypted != "gho_fakeoauthtoken1234567890"  # Must be encrypted

    @pytest.mark.asyncio
    async def test_reconnect_updates_existing_record(self, service, db_session):
        # Create initial record
        existing = DBGitHubIntegration(
            id=str(uuid.uuid4()),
            user_id=FAKE_USER_ID,
            github_user_id="99999",
            github_username="olduser",
            avatar_url="https://old-avatar.com",
            access_token_encrypted=service.encryptor.encrypt("old_token"),
            token_type="bearer",
            scope="repo",
        )
        db_session.add(existing)
        db_session.commit()

        mock_token_data = {
            "access_token": "gho_newtoken",
            "token_type": "bearer",
            "scope": "repo,read:user",
        }
        mock_profile = {
            "id": 99999,
            "login": "newuser",
            "avatar_url": "https://new-avatar.com",
        }

        with patch.object(service, "exchange_code_for_token", new=AsyncMock(return_value=mock_token_data)), \
             patch.object(service, "fetch_github_profile", new=AsyncMock(return_value=mock_profile)):
            record = await service.connect_user_github(FAKE_USER_ID, "new_code")

        assert record.github_username == "newuser"
        count = db_session.query(DBGitHubIntegration).filter_by(user_id=FAKE_USER_ID).count()
        assert count == 1  # Must not create a duplicate


# ─── Status & Disconnect Tests ─────────────────────────────────────────────────

class TestGetStatus:
    def test_status_not_connected_when_no_record(self, service):
        status = service.get_status(FAKE_USER_ID)
        assert status["connected"] is False
        assert status["username"] is None

    def test_status_connected_returns_metadata(self, service, db_session):
        record = DBGitHubIntegration(
            id=str(uuid.uuid4()),
            user_id=FAKE_USER_ID,
            github_user_id="12345",
            github_username="connecteduser",
            avatar_url="https://avatars.github.com/u/12345",
            access_token_encrypted=service.encryptor.encrypt("gho_sometoken"),
            token_type="bearer",
            scope="repo",
            connected_at=datetime.now(timezone.utc),
        )
        db_session.add(record)
        db_session.commit()

        status = service.get_status(FAKE_USER_ID)
        assert status["connected"] is True
        assert status["username"] == "connecteduser"
        assert status["avatar_url"] is not None
        # Never expose token
        assert "token" not in str(status).lower() or "access_token" not in status


class TestDisconnect:
    def test_disconnect_removes_record(self, service, db_session):
        record = DBGitHubIntegration(
            id=str(uuid.uuid4()),
            user_id=FAKE_USER_ID,
            github_user_id="12345",
            github_username="testuser",
            avatar_url=None,
            access_token_encrypted=service.encryptor.encrypt("gho_token"),
            token_type="bearer",
            scope="repo",
        )
        db_session.add(record)
        db_session.commit()

        result = service.disconnect(FAKE_USER_ID)
        assert result is True
        remaining = db_session.query(DBGitHubIntegration).filter_by(user_id=FAKE_USER_ID).first()
        assert remaining is None

    def test_disconnect_nonexistent_returns_false(self, service):
        result = service.disconnect("nonexistent-user-id")
        assert result is False


# ─── Decrypted Token Tests ─────────────────────────────────────────────────────

class TestGetDecryptedToken:
    def test_returns_none_when_not_connected(self, service):
        assert service.get_decrypted_token(FAKE_USER_ID) is None

    def test_returns_correct_token(self, service, db_session):
        raw_token = "gho_plaintextfaketoken"
        record = DBGitHubIntegration(
            id=str(uuid.uuid4()),
            user_id=FAKE_USER_ID,
            github_user_id="77777",
            github_username="tokenuser",
            avatar_url=None,
            access_token_encrypted=service.encryptor.encrypt(raw_token),
            token_type="bearer",
            scope="repo",
        )
        db_session.add(record)
        db_session.commit()

        token = service.get_decrypted_token(FAKE_USER_ID)
        assert token == raw_token
