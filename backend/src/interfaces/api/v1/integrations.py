"""
Integrations API Endpoints
===========================
Provides routes for third-party integrations, starting with GitHub OAuth,
token management, and authorized repository discovery.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from src.core.config import settings
from src.core.logger import logger
from src.application.services.github_integration_service import GitHubIntegrationService
from src.interfaces.api.dependencies import get_current_user, get_db_session
from sqlalchemy.orm import Session

router = APIRouter(prefix="/integrations", tags=["integrations"])


def get_github_integration_service(db_session: Session = Depends(get_db_session)) -> GitHubIntegrationService:
    return GitHubIntegrationService(db_session)


class GitHubStatusResponse(BaseModel):
    connected: bool
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    connected_at: Optional[str] = None


class GitHubConnectResponse(BaseModel):
    auth_url: str


class GitHubRepositoryResponse(BaseModel):
    id: str
    name: str
    full_name: str
    owner: str
    url: str
    clone_url: str
    is_private: bool
    default_branch: str
    description: Optional[str] = ""
    stars: int = 0
    language: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("/github/connect", response_model=GitHubConnectResponse)
def get_github_connect_url(
    current_user: dict = Depends(get_current_user),
    service: GitHubIntegrationService = Depends(get_github_integration_service),
):
    """Generate GitHub OAuth URL with secure CSRF state."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")

    # Fail fast with a clear error if GitHub OAuth is not configured.
    if not settings.GITHUB_CLIENT_ID:
        logger.error(
            "GITHUB_CLIENT_ID is not set. GitHub OAuth cannot proceed. "
            "Add GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET to backend/.env and restart the backend."
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "GitHub OAuth is not configured on this server. "
                "Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in backend/.env and restart the backend."
            ),
        )

    try:
        auth_url = service.get_authorization_url(user_id)
    except RuntimeError as exc:
        logger.error("Failed to generate GitHub OAuth URL", error=str(exc))
        raise HTTPException(status_code=503, detail=str(exc))

    return GitHubConnectResponse(auth_url=auth_url)


@router.get("/github/callback")
async def github_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    service: GitHubIntegrationService = Depends(get_github_integration_service),
):
    """
    OAuth redirect callback from GitHub.
    Exchanges code server-side, encrypts token, and redirects back to frontend.
    """
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    if error:
        logger.warning("GitHub OAuth callback returned error", error=error)
        return RedirectResponse(url=f"{frontend_url}/settings?github_error={error}")

    if not code or not state:
        return RedirectResponse(url=f"{frontend_url}/settings?github_error=missing_code_or_state")

    user_id = service.validate_state(state)
    if not user_id:
        logger.warning("Invalid or expired OAuth state parameter", state=state)
        return RedirectResponse(url=f"{frontend_url}/settings?github_error=invalid_state")

    try:
        await service.connect_user_github(user_id, code)
        return RedirectResponse(url=f"{frontend_url}/settings?github=connected")
    except Exception as exc:
        logger.error("Failed to complete GitHub connection", error=str(exc))
        return RedirectResponse(url=f"{frontend_url}/settings?github_error=connection_failed")


@router.get("/github/status", response_model=GitHubStatusResponse)
def get_github_status(
    current_user: dict = Depends(get_current_user),
    service: GitHubIntegrationService = Depends(get_github_integration_service),
):
    """Return non-secret connection status for the authenticated user."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")

    return service.get_status(user_id)


class GitHubDisconnectResponse(BaseModel):
    connected: bool = False
    message: str = "GitHub account disconnected successfully"


@router.delete("/github/disconnect", response_model=GitHubDisconnectResponse)
@router.delete("/github", response_model=GitHubDisconnectResponse)
def disconnect_github(
    current_user: dict = Depends(get_current_user),
    service: GitHubIntegrationService = Depends(get_github_integration_service),
):
    """Disconnect GitHub account and remove encrypted tokens."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")

    service.disconnect(user_id)
    return GitHubDisconnectResponse(connected=False, message="GitHub account disconnected successfully")


@router.get("/github/repositories", response_model=List[GitHubRepositoryResponse])
async def list_github_repositories(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    service: GitHubIntegrationService = Depends(get_github_integration_service),
):
    """List accessible GitHub repositories for the connected user."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")

    try:
        repos = await service.list_user_repositories(user_id, page=page, per_page=per_page, search=search)
        return repos
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail="Your GitHub connection has expired. Please reconnect GitHub.")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch GitHub repositories: {str(exc)}")
