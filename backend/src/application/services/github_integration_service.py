"""
GitHub Integration Service
===========================
Coordinates GitHub OAuth authentication, encrypted token storage,
account connection lifecycle, and authorized repository listing.
"""
import secrets
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
import httpx
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.logger import logger
from src.infrastructure.persistence.github_models import DBGitHubIntegration
from src.infrastructure.security.token_encryptor import TokenEncryptor


class GitHubIntegrationService:
    """Handles OAuth authorization, server-side token exchange, and GitHub user API operations."""

    # In-memory fallback state cache when Redis is not available: state -> (user_id, created_at)
    _state_cache: Dict[str, Tuple[str, float]] = {}

    def __init__(self, db_session: Session, encryptor: Optional[TokenEncryptor] = None):
        self.db = db_session
        self.encryptor = encryptor or TokenEncryptor()

    def get_authorization_url(self, user_id: str) -> str:
        """
        Generate GitHub OAuth authorization URL with a cryptographically secure CSRF state.
        """
        state = secrets.token_urlsafe(32)
        # Store state in memory with timestamp
        GitHubIntegrationService._state_cache[state] = (user_id, datetime.now(timezone.utc).timestamp())

        client_id = settings.GITHUB_CLIENT_ID or "placeholder_client_id"
        redirect_uri = settings.GITHUB_REDIRECT_URI
        scope = "repo,read:user,user:email"

        auth_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scope}"
            f"&state={state}"
        )
        return auth_url

    def validate_state(self, state: str) -> Optional[str]:
        """Validate CSRF state and return the associated user_id if valid and not expired."""
        if not state or state not in GitHubIntegrationService._state_cache:
            return None

        user_id, created_at = GitHubIntegrationService._state_cache.pop(state)
        now = datetime.now(timezone.utc).timestamp()
        # Expire after 10 minutes (600 seconds)
        if now - created_at > 600:
            return None
        return user_id

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code with GitHub for an access token."""
        url = "https://github.com/login/oauth/access_token"
        payload = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
        }
        headers = {"Accept": "application/json", "User-Agent": "KAI-Code-Studio/1.0"}

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=15.0)
            if resp.status_code != 200:
                raise RuntimeError(f"GitHub token exchange failed: HTTP {resp.status_code}")
            data = resp.json()
            if "error" in data:
                raise RuntimeError(f"GitHub OAuth error: {data.get('error_description', data.get('error'))}")
            return data

    async def fetch_github_profile(self, access_token: str) -> Dict[str, Any]:
        """Fetch basic user profile from GitHub API."""
        url = "https://api.github.com/user"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "KAI-Code-Studio/1.0",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=10.0)
            if resp.status_code != 200:
                raise RuntimeError(f"Failed to fetch GitHub profile: HTTP {resp.status_code}")
            return resp.json()

    async def connect_user_github(self, user_id: str, code: str) -> DBGitHubIntegration:
        """Complete the OAuth callback flow, encrypt token, and persist connection."""
        token_data = await self.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("No access token returned by GitHub")

        profile = await self.fetch_github_profile(access_token)
        encrypted_token = self.encryptor.encrypt(access_token)

        # Upsert integration record
        existing = (
            self.db.query(DBGitHubIntegration)
            .filter(DBGitHubIntegration.user_id == user_id)
            .first()
        )

        if existing:
            existing.github_user_id = str(profile.get("id"))
            existing.github_username = profile.get("login")
            existing.avatar_url = profile.get("avatar_url")
            existing.access_token_encrypted = encrypted_token
            existing.token_type = token_data.get("token_type", "bearer")
            existing.scope = token_data.get("scope", "")
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            new_integration = DBGitHubIntegration(
                id=str(uuid.uuid4()),
                user_id=user_id,
                github_user_id=str(profile.get("id")),
                github_username=profile.get("login"),
                avatar_url=profile.get("avatar_url"),
                access_token_encrypted=encrypted_token,
                token_type=token_data.get("token_type", "bearer"),
                scope=token_data.get("scope", ""),
            )
            self.db.add(new_integration)
            self.db.commit()
            self.db.refresh(new_integration)
            return new_integration

    def get_status(self, user_id: str) -> Dict[str, Any]:
        """Return sanitized connection status without exposing any credentials."""
        integration = (
            self.db.query(DBGitHubIntegration)
            .filter(DBGitHubIntegration.user_id == user_id)
            .first()
        )
        if not integration or not integration.access_token_encrypted:
            return {
                "connected": False,
                "username": None,
                "avatar_url": None,
                "connected_at": None,
            }

        return {
            "connected": True,
            "username": integration.github_username,
            "avatar_url": integration.avatar_url,
            "connected_at": integration.connected_at.isoformat() if integration.connected_at else None,
        }

    def disconnect(self, user_id: str) -> bool:
        """Disconnect GitHub integration and remove stored tokens."""
        integration = (
            self.db.query(DBGitHubIntegration)
            .filter(DBGitHubIntegration.user_id == user_id)
            .first()
        )
        if not integration:
            return False

        self.db.delete(integration)
        self.db.commit()
        return True

    def get_decrypted_token(self, user_id: str) -> Optional[str]:
        """Retrieve and decrypt the user's GitHub access token for backend service usage only."""
        integration = (
            self.db.query(DBGitHubIntegration)
            .filter(DBGitHubIntegration.user_id == user_id)
            .first()
        )
        if not integration or not integration.access_token_encrypted:
            return None
        return self.encryptor.decrypt(integration.access_token_encrypted)

    async def list_user_repositories(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 30,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List repositories accessible to the user's connected GitHub account."""
        token = self.get_decrypted_token(user_id)
        if not token:
            raise ValueError("GitHub account is not connected")

        url = f"https://api.github.com/user/repos?per_page={min(per_page, 100)}&page={page}&sort=updated"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "KAI-Code-Studio/1.0",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=15.0)
            if resp.status_code != 200:
                raise RuntimeError(f"GitHub API Error: {resp.status_code}")
            repos_data = resp.json()

        results = []
        for r in repos_data:
            name = r.get("name", "")
            full_name = r.get("full_name", "")
            desc = r.get("description", "") or ""

            if search:
                s_lower = search.lower()
                if s_lower not in name.lower() and s_lower not in full_name.lower() and s_lower not in desc.lower():
                    continue

            results.append({
                "id": str(r.get("id")),
                "name": name,
                "full_name": full_name,
                "owner": r.get("owner", {}).get("login", ""),
                "url": r.get("html_url", ""),
                "clone_url": r.get("clone_url", ""),
                "is_private": r.get("private", False),
                "default_branch": r.get("default_branch", "main"),
                "description": desc,
                "stars": r.get("stargazers_count", 0),
                "language": r.get("language"),
                "updated_at": r.get("updated_at"),
            })

        return results
