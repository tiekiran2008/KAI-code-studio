"""
test_cors_configuration.py
============================
Unit tests verifying production CORS settings:
1. FRONTEND_URL environment variable is dynamically added to CORS_ORIGINS.
2. Trailing slashes are stripped from FRONTEND_URL and CORS origins.
3. Localhost and 127.0.0.1 origins remain preserved for local development.
4. Wildcard '*' is avoided when credentials are enabled.
5. FastAPI preflight OPTIONS requests return correct Access-Control headers for Vercel frontend.
"""
import pytest
from fastapi.testclient import TestClient
from src.core.config import Settings
from src.main import app

VERCEL_FRONTEND_URL = "https://kai-code-studio-h83nbpgfj-kiran08461kumar-9455s-projects.vercel.app"


def test_frontend_url_dynamically_added_to_cors_origins(monkeypatch):
    """Verifies FRONTEND_URL env var is automatically appended to CORS_ORIGINS."""
    monkeypatch.setenv("FRONTEND_URL", VERCEL_FRONTEND_URL)
    settings = Settings()

    assert VERCEL_FRONTEND_URL in settings.CORS_ORIGINS


def test_trailing_slash_stripped_from_frontend_url(monkeypatch):
    """Verifies trailing slash is stripped from FRONTEND_URL before adding to CORS_ORIGINS."""
    monkeypatch.setenv("FRONTEND_URL", f"{VERCEL_FRONTEND_URL}/")
    settings = Settings()

    assert VERCEL_FRONTEND_URL in settings.CORS_ORIGINS
    assert f"{VERCEL_FRONTEND_URL}/" not in settings.CORS_ORIGINS


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


def test_no_wildcard_when_credentials_enabled():
    """Verifies wildcard '*' is avoided when credentials are enabled."""
    settings = Settings()
    assert "*" not in settings.CORS_ORIGINS


def test_cors_preflight_options_response(monkeypatch):
    """Verifies preflight OPTIONS request returns correct CORS headers for Vercel frontend."""
    monkeypatch.setenv("FRONTEND_URL", VERCEL_FRONTEND_URL)
    from src.core.config import Settings
    from starlette.middleware.cors import CORSMiddleware
    from fastapi import FastAPI

    test_app = FastAPI()
    test_settings = Settings()

    @test_app.get("/health")
    def health():
        return {"status": "ok"}

    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=test_settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    client = TestClient(test_app)

    response = client.options(
        "/health",
        headers={
            "Origin": VERCEL_FRONTEND_URL,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == VERCEL_FRONTEND_URL
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "GET" in response.headers.get("access-control-allow-methods", "")
