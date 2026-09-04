import pytest
import uuid
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.core.config import settings
from src.interfaces.api.dependencies import get_current_user, UserPayload

# Create a small dummy FastAPI application to isolate and test get_current_user dependency behavior
test_app = FastAPI()

@test_app.get("/test-auth")
def dummy_auth_route(current_user: UserPayload = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}

@pytest.fixture
def clean_settings():
    # Save current settings state
    orig_bypass = settings.DEV_AUTH_BYPASS
    orig_env = settings.ENVIRONMENT
    orig_email = settings.DEV_AUTH_USER_EMAIL
    yield
    # Restore settings state
    settings.DEV_AUTH_BYPASS = orig_bypass
    settings.ENVIRONMENT = orig_env
    settings.DEV_AUTH_USER_EMAIL = orig_email

class TestAuthDependency:
    def test_normal_jwt_authentication_success(self, clean_settings):
        """Test normal JWT authentication with a valid token."""
        settings.DEV_AUTH_BYPASS = False
        settings.ENVIRONMENT = "development"
        
        mock_payload = {"sub": "user-uuid-1234", "email": "valid-user@example.com"}
        
        # Patch validate_token to return mock payload
        with patch("src.application.services.auth_service.AuthService.validate_token") as mock_validate:
            mock_validate.return_value = mock_payload
            client = TestClient(test_app)
            
            resp = client.get("/test-auth", headers={"Authorization": "Bearer valid-token"})
            assert resp.status_code == 200
            assert resp.json() == {"id": "user-uuid-1234", "email": "valid-user@example.com"}
            mock_validate.assert_called_once_with("valid-token")

    def test_normal_jwt_authentication_invalid_token(self, clean_settings):
        """Test normal JWT authentication with an invalid token raises 401."""
        settings.DEV_AUTH_BYPASS = False
        settings.ENVIRONMENT = "development"
        
        with patch("src.application.services.auth_service.AuthService.validate_token") as mock_validate:
            mock_validate.side_effect = ValueError("Invalid token")
            client = TestClient(test_app)
            
            resp = client.get("/test-auth", headers={"Authorization": "Bearer bad-token"})
            assert resp.status_code == 401
            assert resp.json()["detail"] == "Invalid token"

    def test_unauthenticated_request_rejection(self, clean_settings):
        """Test that unauthenticated requests are rejected when bypass is disabled."""
        settings.DEV_AUTH_BYPASS = False
        settings.ENVIRONMENT = "development"
        
        client = TestClient(test_app)
        resp = client.get("/test-auth")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Not authenticated"

    def test_development_bypass_when_explicitly_enabled(self, clean_settings):
        """Test development bypass when explicitly enabled (without token, returning deterministic dev user)."""
        settings.DEV_AUTH_BYPASS = True
        settings.ENVIRONMENT = "development"
        settings.DEV_AUTH_USER_EMAIL = "developer@example.com"
        
        client = TestClient(test_app)
        resp = client.get("/test-auth")
        assert resp.status_code == 200
        
        # Determine expected deterministic UUID
        expected_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, "developer@example.com"))
        assert resp.json() == {"id": expected_uuid, "email": "developer@example.com"}

    def test_production_configuration_cannot_use_bypass(self, clean_settings):
        """Test that production environment overrides/disables bypass even if DEV_AUTH_BYPASS is set to True."""
        settings.DEV_AUTH_BYPASS = True
        settings.ENVIRONMENT = "production"
        
        client = TestClient(test_app)
        resp = client.get("/test-auth")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Not authenticated"
