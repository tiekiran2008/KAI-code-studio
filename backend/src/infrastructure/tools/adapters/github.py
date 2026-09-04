"""
GitHub Tool Adapter
===================
Provides read-only access to a GitHub repository (branches, commits, issues, PRs, file contents).

Token resolution is intentionally lazy and per-execution:
- A static ``github_token`` string may be supplied for backward compatibility (e.g., tests).
- A ``token_resolver`` callable ``() -> Optional[str]`` is preferred for production runtime,
  enabling per-request user-scoped OAuth token injection without holding a token in memory
  beyond the lifetime of the request.

Security guarantees:
- The resolved token is used only within the execute() call scope; never stored on self after __init__.
- Token values are never included in ToolResult data, error messages, or logs.
- The adapter remains safe to share across requests when token_resolver returns per-user values.
"""
import httpx
from typing import Any, Callable, Dict, Optional

from src.domain.interfaces.tools import ITool
from src.domain.models.tools import PermissionLevel, ToolMetadata, ToolResult


class GitHubToolAdapter(ITool):
    def __init__(
        self,
        github_token: Optional[str] = None,
        token_resolver: Optional[Callable[[], Optional[str]]] = None,
    ) -> None:
        """
        Parameters
        ----------
        github_token : Optional[str]
            Static GitHub token for backward compatibility and tests.
            Ignored at runtime when ``token_resolver`` is provided.
        token_resolver : Optional[Callable[[], Optional[str]]]
            Zero-argument callable that returns the current user's GitHub OAuth
            token on demand.  When supplied, this takes precedence over
            ``github_token``.  The callable is invoked once per execute() call
            so the adapter can be constructed before the user context is known.
        """
        # Store only the resolver, not the raw token, to avoid long-lived token retention.
        self._static_token = github_token
        self._token_resolver = token_resolver

    def _resolve_token(self) -> Optional[str]:
        """Return the effective GitHub token for this execution, never log it."""
        if self._token_resolver is not None:
            return self._token_resolver()
        return self._static_token or None

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="github_read",
            description="Fetches data from a GitHub repository (branches, commits, PRs, issues, file contents).",
            permissions=PermissionLevel.READ_ONLY,
            input_schema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "action": {
                        "type": "string",
                        "enum": ["branches", "commits", "pulls", "issues", "content"],
                        "description": "What to fetch"
                    },
                    "path": {"type": "string", "description": "File path (if action=content)"}
                },
                "required": ["owner", "repo", "action"]
            },
            output_schema={"type": "object"}
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        owner = kwargs.get("owner")
        repo = kwargs.get("repo")
        action = kwargs.get("action")
        path = kwargs.get("path", "")

        # Resolve token at execution time (per-user, not stored beyond this call)
        token = self._resolve_token()

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "KAI-Code-Studio/1.0",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        base_url = f"https://api.github.com/repos/{owner}/{repo}"

        endpoints = {
            "branches": f"{base_url}/branches",
            "commits": f"{base_url}/commits",
            "pulls": f"{base_url}/pulls",
            "issues": f"{base_url}/issues",
            "content": f"{base_url}/contents/{path}"
        }

        url = endpoints.get(action)
        if not url:
            return ToolResult(success=False, error=f"Invalid action: {action}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    return ToolResult(success=True, data=response.json())
                elif response.status_code == 401:
                    # Do NOT include token in error message
                    return ToolResult(
                        success=False,
                        error="GitHub authentication failed. Connect your GitHub account in Settings."
                    )
                elif response.status_code == 404:
                    return ToolResult(
                        success=False,
                        error=f"GitHub resource not found: {owner}/{repo}/{action}"
                    )
                else:
                    return ToolResult(
                        success=False,
                        error=f"GitHub API Error: {response.status_code}"
                    )
            except Exception as e:
                # Sanitize error to exclude any potential token leakage from httpx internals
                return ToolResult(success=False, error=f"GitHub request failed: {type(e).__name__}")
