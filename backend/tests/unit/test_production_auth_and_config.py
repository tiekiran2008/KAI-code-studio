"""
test_production_auth_and_config.py
====================================
Tests for production authentication and configuration fixes.
"""
import pytest
from unittest.mock import MagicMock, patch
from src.core.config import Settings


class TestValidateTokenSupabaseApiCall:
    @patch("src.application.services.auth_service.create_client")
    @patch("src.application.services.auth_service.settings")
    def test_valid_token_calls_get_user_with_jwt_kwarg(self, mock_settings, mock_create_client):
        """get_user must be called with jwt=<token> so supabase-py sends
        Authorization: Bearer header to /auth/v1/user."""
        mock_settings.SUPABASE_URL = "https://ofdvllzzwamyymovzkhc.supabase.co"
        mock_settings.SUPABASE_KEY = ""
        mock_settings.SUPABASE_ANON_KEY = "test-anon-key"
        mock_settings.SUPABASE_JWT_SECRET = ""
        mock_settings.ENVIRONMENT = "production"
        mock_settings.DEV_AUTH_BYPASS = False
        mock_settings.get_supabase_config_status.return_value = {
            "SUPABASE_URL": True, "SUPABASE_ANON_KEY": True,
            "SUPABASE_JWT_SECRET": False, "SUPABASE_SERVICE_ROLE_KEY": False,
        }

        mock_user = MagicMock()
        mock_user.id = "google-oauth-user-abc"
        mock_user.email = "user@example.com"
        mock_user.role = "authenticated"
        mock_user.user_metadata = {}
        mock_user.app_metadata = {"provider": "google"}

        mock_res = MagicMock()
        mock_res.user = mock_user

        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.return_value = mock_res
        mock_create_client.return_value = mock_supabase

        from src.application.services.auth_service import AuthService
        service = AuthService()
        payload = service.validate_token("valid-supabase-access-token")

        mock_supabase.auth.get_user.assert_called_once_with(jwt="valid-supabase-access-token")
        assert payload["sub"] == "google-oauth-user-abc"
        assert payload["email"] == "user@example.com"

    @patch("src.application.services.auth_service.create_client")
    @patch("src.application.services.auth_service.settings")
    def test_supabase_403_surfaces_real_error_message(self, mock_settings, mock_create_client):
        """A 403 from Supabase must surface as ValueError with the real message."""
        from supabase_auth.errors import AuthApiError

        mock_settings.SUPABASE_URL = "https://ofdvllzzwamyymovzkhc.supabase.co"
        mock_settings.SUPABASE_KEY = ""
        mock_settings.SUPABASE_ANON_KEY = "wrong-anon-key"
        mock_settings.SUPABASE_JWT_SECRET = ""
        mock_settings.ENVIRONMENT = "production"
        mock_settings.DEV_AUTH_BYPASS = False
        mock_settings.get_supabase_config_status.return_value = {
            "SUPABASE_URL": True, "SUPABASE_ANON_KEY": True,
            "SUPABASE_JWT_SECRET": False, "SUPABASE_SERVICE_ROLE_KEY": False,
        }

        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.side_effect = AuthApiError("Invalid API key", 403, None)
        mock_create_client.return_value = mock_supabase

        from src.application.services.auth_service import AuthService
        service = AuthService()

        with pytest.raises(ValueError) as exc_info:
            service.validate_token("any-token")

        error_msg = str(exc_info.value)
        assert "Invalid API key" in error_msg or "Supabase auth error" in error_msg

    @patch("src.application.services.auth_service.settings")
    def test_missing_supabase_config_raises_config_error(self, mock_settings):
        """Missing SUPABASE_URL and SUPABASE_ANON_KEY must raise a clear config error."""
        mock_settings.SUPABASE_URL = ""
        mock_settings.SUPABASE_KEY = ""
        mock_settings.SUPABASE_ANON_KEY = ""
        mock_settings.SUPABASE_JWT_SECRET = ""
        mock_settings.ENVIRONMENT = "production"
        mock_settings.DEV_AUTH_BYPASS = False
        mock_settings.get_supabase_config_status.return_value = {
            "SUPABASE_URL": False, "SUPABASE_ANON_KEY": False,
            "SUPABASE_JWT_SECRET": False, "SUPABASE_SERVICE_ROLE_KEY": False,
        }

        from src.application.services.auth_service import AuthService
        service = AuthService()

        with pytest.raises(ValueError) as exc_info:
            service.validate_token("some-token")

        error_msg = str(exc_info.value).lower()
        assert "supabase" in error_msg or "not configured" in error_msg

    @patch("src.application.services.auth_service.create_client")
    @patch("src.application.services.auth_service.settings")
    def test_valid_jwt_secret_skips_supabase_api(self, mock_settings, mock_create_client):
        """With SUPABASE_JWT_SECRET set and valid token, Supabase API must NOT be called."""
        import jwt as pyjwt

        secret = "test-jwt-secret-32-bytes-exactly!"
        mock_settings.SUPABASE_JWT_SECRET = secret
        mock_settings.SUPABASE_URL = "https://ofdvllzzwamyymovzkhc.supabase.co"
        mock_settings.SUPABASE_KEY = ""
        mock_settings.SUPABASE_ANON_KEY = "anon-key"
        mock_settings.ENVIRONMENT = "production"
        mock_settings.DEV_AUTH_BYPASS = False
        mock_settings.get_supabase_config_status.return_value = {
            "SUPABASE_URL": True, "SUPABASE_ANON_KEY": True,
            "SUPABASE_JWT_SECRET": True, "SUPABASE_SERVICE_ROLE_KEY": False,
        }

        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase

        token = pyjwt.encode({"sub": "user-123", "email": "test@example.com"}, secret, algorithm="HS256")

        from src.application.services.auth_service import AuthService
        service = AuthService()
        payload = service.validate_token(token)

        assert payload["sub"] == "user-123"
        mock_supabase.auth.get_user.assert_not_called()


class TestDatabaseUrlNormalization:
    def test_pgbouncer_param_stripped(self, monkeypatch):
        """?pgbouncer=true must be stripped (psycopg2 rejects it)."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgres://user:pass@db.supabase.co:5432/postgres?pgbouncer=true"
        )
        settings = Settings()
        assert "pgbouncer" not in settings.POSTGRES_URL
        assert settings.POSTGRES_URL.startswith("postgresql://")

    def test_sslmode_param_stripped(self, monkeypatch):
        """?sslmode=require must be stripped from the DSN."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://user:pass@db.supabase.co:5432/postgres?sslmode=require"
        )
        settings = Settings()
        assert "sslmode" not in settings.POSTGRES_URL

    def test_pgbouncer_and_sslmode_both_stripped(self, monkeypatch):
        """Both pgbouncer=true and sslmode=require are stripped together."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgres://user:pass@db.supabase.co:5432/postgres?pgbouncer=true&sslmode=require"
        )
        settings = Settings()
        assert "pgbouncer" not in settings.POSTGRES_URL
        assert "sslmode" not in settings.POSTGRES_URL
        assert settings.POSTGRES_URL.startswith("postgresql://")

    def test_clean_url_unchanged(self, monkeypatch):
        """Clean DATABASE_URL without suspicious params passes through unchanged."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgres://render_user:secret@render-db.render.com:5432/render_db"
        )
        settings = Settings()
        assert settings.POSTGRES_URL == "postgresql://render_user:secret@render-db.render.com:5432/render_db"

    def test_safe_params_preserved(self, monkeypatch):
        """Safe query params not in the block-list are preserved."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://user:pass@host:5432/db?pgbouncer=true&connect_timeout=10"
        )
        settings = Settings()
        assert "pgbouncer" not in settings.POSTGRES_URL
        assert "connect_timeout=10" in settings.POSTGRES_URL


class TestSupabaseConfigDiagnostic:
    def test_returns_booleans_not_secret_values(self, monkeypatch):
        """get_supabase_config_status must return only booleans, never secret strings."""
        monkeypatch.setenv("SUPABASE_URL", "https://ofdvllzzwamyymovzkhc.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key-value")
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret-value")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")

        settings = Settings()
        status = settings.get_supabase_config_status()

        assert isinstance(status, dict)
        for key, value in status.items():
            assert isinstance(value, bool), f"{key} should be bool, got {type(value)}"

        assert status["SUPABASE_URL"] is True
        assert status["SUPABASE_ANON_KEY"] is True
        assert status["SUPABASE_JWT_SECRET"] is True
        assert status["SUPABASE_SERVICE_ROLE_KEY"] is False

    def test_all_missing_returns_all_false(self, monkeypatch):
        """When no Supabase vars are set, all status flags are False."""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
        monkeypatch.delenv("SUPABASE_KEY", raising=False)
        monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

        settings = Settings(
            SUPABASE_URL="",
            SUPABASE_KEY="",
            SUPABASE_ANON_KEY="",
            SUPABASE_JWT_SECRET="",
            SUPABASE_SERVICE_ROLE_KEY="",
        )
        status = settings.get_supabase_config_status()

        assert status["SUPABASE_URL"] is False
        assert status["SUPABASE_ANON_KEY"] is False
        assert status["SUPABASE_JWT_SECRET"] is False


class TestRedisKwargs:
    def test_rediss_url_adds_ssl_cert_reqs_and_timeout(self, monkeypatch):
        """rediss:// must configure ssl_cert_reqs=None and socket_connect_timeout."""
        monkeypatch.setenv("REDIS_URL", "rediss://default:secret@upstash.upstash.io:6379")
        settings = Settings()
        kwargs = settings.get_redis_kwargs()

        assert kwargs["ssl_cert_reqs"] is None
        assert "socket_connect_timeout" in kwargs
        assert kwargs["socket_connect_timeout"] > 0

    def test_plain_redis_url_no_ssl(self, monkeypatch):
        """Non-TLS redis:// URLs must not have ssl_cert_reqs."""
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        settings = Settings()
        kwargs = settings.get_redis_kwargs()

        assert "ssl_cert_reqs" not in kwargs
        assert "socket_connect_timeout" in kwargs
