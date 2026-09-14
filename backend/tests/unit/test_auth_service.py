import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from src.application.services.auth_service import AuthService
from src.domain.entities.user import UserSession

class TestAuthServiceSignup:
    @patch("src.application.services.auth_service.create_client")
    @patch("src.application.services.auth_service.settings")
    def test_signup_email_confirmation_required(self, mock_settings, mock_create_client):
        mock_settings.SUPABASE_URL = "https://mock.supabase.co"
        mock_settings.SUPABASE_KEY = "mock_key"
        mock_settings.SUPABASE_ANON_KEY = "mock_key"

        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase

        # Mock Supabase response when email confirmation is enabled (user != None, session == None)
        mock_user = MagicMock()
        mock_user.id = "user-uuid-123"
        mock_user.email = "test@example.com"
        mock_user.created_at = datetime.now()

        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = None
        mock_supabase.auth.sign_up.return_value = mock_response

        service = AuthService()
        result = service.signup("test@example.com", "password123")

        assert isinstance(result, UserSession)
        assert result.user.id == "user-uuid-123"
        assert result.user.email == "test@example.com"
        assert result.access_token is None
        assert result.refresh_token is None
        assert result.confirmation_required is True
        assert "confirm your account" in result.message

    @patch("src.application.services.auth_service.create_client")
    @patch("src.application.services.auth_service.settings")
    def test_signup_with_active_session(self, mock_settings, mock_create_client):
        mock_settings.SUPABASE_URL = "https://mock.supabase.co"
        mock_settings.SUPABASE_KEY = "mock_key"
        mock_settings.SUPABASE_ANON_KEY = "mock_key"

        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase

        # Mock Supabase response when email confirmation is disabled (user != None, session != None)
        mock_user = MagicMock()
        mock_user.id = "user-uuid-456"
        mock_user.email = "active@example.com"
        mock_user.created_at = datetime.now()

        mock_session = MagicMock()
        mock_session.access_token = "valid_access_token"
        mock_session.refresh_token = "valid_refresh_token"
        mock_session.expires_in = 3600

        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session
        mock_supabase.auth.sign_up.return_value = mock_response

        service = AuthService()
        result = service.signup("active@example.com", "password123")

        assert isinstance(result, UserSession)
        assert result.user.id == "user-uuid-456"
        assert result.access_token == "valid_access_token"
        assert result.refresh_token == "valid_refresh_token"
        assert result.confirmation_required is False

class TestAuthServiceDevConfirmation:
    @patch("src.application.services.auth_service.create_client")
    @patch("src.application.services.auth_service.settings")
    def test_confirm_user_email_success(self, mock_settings, mock_create_client):
        mock_settings.ENVIRONMENT = "development"
        mock_settings.SUPABASE_URL = "https://mock.supabase.co"
        mock_settings.SUPABASE_SERVICE_ROLE_KEY = "mock_service_key"
        mock_settings.SUPABASE_KEY = ""

        mock_user = MagicMock()
        mock_user.id = "defd75bb-cb1c-473a-b920-466035872214"
        mock_user.email = "test@example.com"

        mock_res = MagicMock()
        mock_res.user = mock_user

        mock_admin_client = MagicMock()
        mock_admin_client.auth.admin.update_user_by_id.return_value = mock_res
        mock_create_client.return_value = mock_admin_client

        service = AuthService()
        res = service.confirm_user_email("defd75bb-cb1c-473a-b920-466035872214")

        assert res["status"] == "success"
        assert res["user_id"] == "defd75bb-cb1c-473a-b920-466035872214"
        assert res["confirmed"] is True
        mock_admin_client.auth.admin.update_user_by_id.assert_called_once_with("defd75bb-cb1c-473a-b920-466035872214", {"email_confirm": True})

    @patch("src.application.services.auth_service.settings")
    def test_confirm_user_email_rejected_in_production(self, mock_settings):
        mock_settings.ENVIRONMENT = "production"
        mock_settings.SUPABASE_URL = "https://mock.supabase.co"
        mock_settings.SUPABASE_KEY = "mock_key"
        mock_settings.SUPABASE_ANON_KEY = "mock_key"

        service = AuthService()
        with pytest.raises(ValueError, match="disabled in production"):
            service.confirm_user_email("defd75bb-cb1c-473a-b920-466035872214")


class TestAuthServiceDevResetPassword:
    @patch("src.application.services.auth_service.create_client")
    @patch("src.application.services.auth_service.settings")
    def test_reset_dev_user_password_success(self, mock_settings, mock_create_client):
        mock_settings.ENVIRONMENT = "development"
        mock_settings.DEV_AUTH_BYPASS = True
        mock_settings.SUPABASE_URL = "https://mock.supabase.co"
        mock_settings.SUPABASE_SERVICE_ROLE_KEY = "mock_service_key"
        mock_settings.SUPABASE_KEY = ""

        mock_user = MagicMock()
        mock_user.id = "defd75bb-cb1c-473a-b920-466035872214"
        mock_user.email = "kiran08461kumar@gmail.com"

        mock_res = MagicMock()
        mock_res.user = mock_user

        mock_admin_client = MagicMock()
        mock_admin_client.auth.admin.update_user_by_id.return_value = mock_res
        mock_create_client.return_value = mock_admin_client

        service = AuthService()
        res = service.reset_dev_user_password("defd75bb-cb1c-473a-b920-466035872214", "NewValidPass123!")

        assert res["status"] == "success"
        assert res["user_id"] == "defd75bb-cb1c-473a-b920-466035872214"
        assert res["email"] == "kiran08461kumar@gmail.com"
        mock_admin_client.auth.admin.update_user_by_id.assert_called_once_with(
            "defd75bb-cb1c-473a-b920-466035872214",
            {"password": "NewValidPass123!"}
        )

    @patch("src.application.services.auth_service.settings")
    def test_reset_dev_user_password_rejected_in_production(self, mock_settings):
        mock_settings.ENVIRONMENT = "production"
        mock_settings.DEV_AUTH_BYPASS = True
        mock_settings.SUPABASE_URL = "https://mock.supabase.co"
        mock_settings.SUPABASE_KEY = "mock_key"

        service = AuthService()
        with pytest.raises(ValueError, match="disabled in production"):
            service.reset_dev_user_password("defd75bb-cb1c-473a-b920-466035872214", "NewValidPass123!")

    @patch("src.application.services.auth_service.settings")
    def test_reset_dev_user_password_rejected_when_bypass_false(self, mock_settings):
        mock_settings.ENVIRONMENT = "development"
        mock_settings.DEV_AUTH_BYPASS = False
        mock_settings.SUPABASE_URL = "https://mock.supabase.co"
        mock_settings.SUPABASE_KEY = "mock_key"

        service = AuthService()
        with pytest.raises(ValueError, match="disabled in production environments or when DEV_AUTH_BYPASS is disabled"):
            service.reset_dev_user_password("defd75bb-cb1c-473a-b920-466035872214", "NewValidPass123!")


class TestAuthServiceValidateToken:
    @patch("src.application.services.auth_service.settings")
    def test_validate_token_with_jwt_secret(self, mock_settings):
        import jwt
        mock_settings.ENVIRONMENT = "production"
        mock_settings.DEV_AUTH_BYPASS = False
        mock_settings.SUPABASE_JWT_SECRET = "super-secret-jwt-key"
        mock_settings.SUPABASE_URL = ""
        mock_settings.SUPABASE_KEY = ""

        token = jwt.encode({"sub": "usr-123", "email": "test@example.com"}, "super-secret-jwt-key", algorithm="HS256")
        service = AuthService()
        payload = service.validate_token(token)

        assert payload["sub"] == "usr-123"
        assert payload["email"] == "test@example.com"

    @patch("src.application.services.auth_service.create_client")
    @patch("src.application.services.auth_service.settings")
    def test_validate_token_with_supabase_client_fallback(self, mock_settings, mock_create_client):
        mock_settings.ENVIRONMENT = "production"
        mock_settings.DEV_AUTH_BYPASS = False
        mock_settings.SUPABASE_JWT_SECRET = ""  # No local secret available
        mock_settings.SUPABASE_URL = "https://mock.supabase.co"
        mock_settings.SUPABASE_KEY = "mock_key"
        mock_settings.SUPABASE_ANON_KEY = "mock_key"

        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase

        mock_user = MagicMock()
        mock_user.id = "oauth-google-user-789"
        mock_user.email = "google.user@example.com"
        mock_user.role = "authenticated"
        mock_user.user_metadata = {"full_name": "Google User"}
        mock_user.app_metadata = {"provider": "google"}

        mock_res = MagicMock()
        mock_res.user = mock_user
        mock_supabase.auth.get_user.return_value = mock_res

        service = AuthService()
        payload = service.validate_token("supabase-oauth-access-token")

        assert payload["sub"] == "oauth-google-user-789"
        assert payload["email"] == "google.user@example.com"
        mock_supabase.auth.get_user.assert_called_once_with(jwt="supabase-oauth-access-token")

    @patch("src.application.services.auth_service.settings")
    def test_validate_token_invalid_rejected(self, mock_settings):
        mock_settings.ENVIRONMENT = "production"
        mock_settings.DEV_AUTH_BYPASS = False
        mock_settings.SUPABASE_JWT_SECRET = "super-secret-jwt-key"
        mock_settings.SUPABASE_URL = ""
        mock_settings.SUPABASE_KEY = ""

        service = AuthService()
        with pytest.raises(ValueError, match="Invalid token"):
            service.validate_token("completely-invalid-garbage-token")


class TestProtectedEndpointsAuth:
    def test_unauthenticated_request_returns_401(self, monkeypatch):
        from fastapi.testclient import TestClient
        from src.main import app
        from src.core.config import settings
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "DEV_AUTH_BYPASS", False)

        client = TestClient(app)
        response = client.get("/api/v1/workspaces")
        assert response.status_code == 401
        assert "Not authenticated" in response.json().get("detail", "")

    def test_invalid_bearer_token_returns_401(self, monkeypatch):
        from fastapi.testclient import TestClient
        from src.main import app
        from src.core.config import settings
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "DEV_AUTH_BYPASS", False)
        monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "super-secret-jwt-key-32-bytes-long!")

        client = TestClient(app)
        response = client.get(
            "/api/v1/workspaces",
            headers={"Authorization": "Bearer invalid-forged-token"},
        )
        assert response.status_code == 401

    def test_authenticated_request_with_valid_jwt_succeeds(self, monkeypatch):
        import jwt
        from fastapi.testclient import TestClient
        from src.main import app
        from src.core.config import settings
        secret = "super-secret-jwt-key-32-bytes-long!"
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "DEV_AUTH_BYPASS", False)
        monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", secret)

        valid_token = jwt.encode(
            {"sub": "usr-prod-valid-1", "email": "prod.user@example.com"},
            secret,
            algorithm="HS256",
        )

        client = TestClient(app)
        response = client.get(
            "/api/v1/workspaces",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        # Auth passed; status should be 200 (or successful list of workspaces)
        assert response.status_code == 200




