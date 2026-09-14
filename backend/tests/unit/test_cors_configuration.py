"""
test_cors_configuration.py
============================
Unit tests verifying production CORS settings:
1. Exact Vercel production origin (kai-code-studio-git-master-kiran08461kumar-9455s-projects.vercel.app) is allowed.
2. Production custom domain (kai-code-studio.vercel.app) is allowed.
3. FRONTEND_URL environment variable is dynamically added to CORS_ORIGINS.
4. Trailing slashes and quotes are stripped safely from FRONTEND_URL and CORS origins.
5. Localhost and 127.0.0.1 origins remain preserved for local development.
6. Wildcard '*' is avoided when credentials are enabled.
7. FastAPI preflight OPTIONS requests return correct Access-Control headers for Vercel frontend.
8. Allowed methods include GET, POST, PUT, PATCH, DELETE, OPTIONS.
9. Allowed headers include Authorization and Content-Type.
"""
import pytest
from fastapi.testclient import TestClient
from src.core.config import Settings
from src.main import app

VERCEL_GIT_MASTER_URL = "https://kai-code-studio-git-master-kiran08461kumar-9455s-projects.vercel.app"
VERCEL_PROD_URL = "https://kai-code-studio.vercel.app"
VERCEL_PREVIEW_URL = "https://kai-code-studio-h83nbpgfj-kiran08461kumar-9455s-projects.vercel.app"


def test_production_vercel_origins_in_default_cors_origins():
    """Verifies that key production Vercel origins are pre-configured in CORS_ORIGINS."""
    settings = Settings()
    assert VERCEL_GIT_MASTER_URL in settings.CORS_ORIGINS
    assert VERCEL_PROD_URL in settings.CORS_ORIGINS
    assert VERCEL_PREVIEW_URL in settings.CORS_ORIGINS


def test_frontend_url_dynamically_added_to_cors_origins(monkeypatch):
    """Verifies FRONTEND_URL env var is automatically appended to CORS_ORIGINS."""
    custom_url = "https://custom-preview-branch.vercel.app"
    monkeypatch.setenv("FRONTEND_URL", custom_url)
    settings = Settings()

    assert custom_url in settings.CORS_ORIGINS


def test_trailing_slash_and_quotes_stripped_from_frontend_url(monkeypatch):
    """Verifies trailing slash and quotes are stripped from FRONTEND_URL before adding to CORS_ORIGINS."""
    custom_url = "https://custom-preview-branch-slash.vercel.app"
    monkeypatch.setenv("FRONTEND_URL", f'"{custom_url}/"')
    settings = Settings()

    assert custom_url in settings.CORS_ORIGINS
    assert f"{custom_url}/" not in settings.CORS_ORIGINS


def test_localhost_and_127_0_0_1_origins_preserved():
    """Verifies local development origins remain preserved."""
    settings = Settings()

    for local_origin in [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]:
        assert local_origin in settings.CORS_ORIGINS


def test_no_wildcard_when_credentials_enabled(monkeypatch):
    """Verifies wildcard '*' is avoided when credentials are enabled."""
    monkeypatch.setenv("FRONTEND_URL", "*")
    settings = Settings()
    assert "*" not in settings.CORS_ORIGINS


@pytest.mark.parametrize("origin", [VERCEL_GIT_MASTER_URL, VERCEL_PROD_URL])
def test_cors_preflight_options_response_on_main_app(origin):
    """Verifies preflight OPTIONS request on actual main app returns correct CORS headers for Vercel origins."""
    client = TestClient(app)

    response = client.options(
        "/api/v1/workspaces",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"

    allowed_methods = response.headers.get("access-control-allow-methods", "")
    for method in ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]:
        assert method in allowed_methods

    allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "authorization" in allowed_headers
    assert "content-type" in allowed_headers


def test_cors_preflight_regex_match_for_dynamic_preview():
    """Verifies that arbitrary kai-code-studio preview URLs match the CORS regex."""
    client = TestClient(app)
    preview_origin = "https://kai-code-studio-pr-42-kiran08461kumar-9455s-projects.vercel.app"

    response = client.options(
        "/api/v1/workspaces",
        headers={
            "Origin": preview_origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == preview_origin
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.parametrize("origin", [VERCEL_GIT_MASTER_URL, VERCEL_PROD_URL])
def test_cors_preflight_with_x_user_id_header(origin):
    """
    Verifies that preflight OPTIONS requests including the frontend's three
    custom headers — Authorization, X-User-ID, Content-Type — are accepted
    with HTTP 200 and the correct CORS allow-headers echoed back.

    This is the exact scenario that was failing in production: protected
    endpoints (/workspaces, /teams, /repositories, /integrations/github/connect)
    sent these three headers, but X-User-ID was not listed in allow_headers,
    causing the browser to block the request.
    """
    client = TestClient(app)

    response = client.options(
        "/api/v1/workspaces",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,x-user-id,content-type",
        },
    )

    assert response.status_code == 200, (
        f"Preflight failed with {response.status_code} for origin={origin}"
    )
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"

    allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "authorization" in allowed_headers, "Authorization must be in Access-Control-Allow-Headers"
    assert "x-user-id" in allowed_headers, "X-User-ID must be in Access-Control-Allow-Headers"
    assert "content-type" in allowed_headers, "Content-Type must be in Access-Control-Allow-Headers"
