"""
GitHub Pull Request Service
============================
Dedicated, narrow adapter for creating and reconciling GitHub Pull Requests.

Security & Design Constraints:
- Narrow boundary: ONLY creates and queries Pull Requests
- Zero merge, zero approval, zero branch deletion, zero issue creation
- Zero shell execution, zero LLM integration
- Sanitized credential handling with zero token leakage in logs/messages
- Strict URL validation on provider responses
"""
from datetime import datetime, timezone
import re
from typing import Any, Dict, Optional, Tuple
import httpx

from src.core.logger import logger
from src.domain.entities.git import GitPullRequestResult, GitPullRequestStatusEnum


class GitHubPullRequestService:
    """Narrow adapter for interacting with GitHub Pull Request API."""

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None) -> None:
        self._http_client = http_client

    def _get_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SoftwareEngineeringAIAgent/1.0",
        }
        if token and token.strip():
            headers["Authorization"] = f"Bearer {token.strip()}"
        return headers

    def _mask_error(self, err_text: str) -> str:
        """Strip any tokens or secrets from error text."""
        if not err_text:
            return ""
        # Redact token patterns
        sanitized = re.sub(r'(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82}|Bearer\s+[^\s"]+)', '[REDACTED_TOKEN]', err_text)
        return sanitized[:500]

    async def find_existing_pull_request(
        self,
        owner: str,
        repo: str,
        head_branch: str,
        base_branch: str,
        token: Optional[str] = None,
    ) -> Optional[GitPullRequestResult]:
        """Find an existing open pull request for the given head and base branches."""
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        params = {
            "state": "open",
            "head": f"{owner}:{head_branch}",
            "base": base_branch,
        }
        headers = self._get_headers(token)

        try:
            if self._http_client:
                resp = await self._http_client.get(url, params=params, headers=headers, timeout=10.0)
            else:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, params=params, headers=headers, timeout=10.0)

            if resp.status_code == 200:
                pulls = resp.json()
                if isinstance(pulls, list) and len(pulls) > 0:
                    pr_data = pulls[0]
                    pr_num = pr_data.get("number")
                    pr_url = pr_data.get("html_url")
                    pr_title = pr_data.get("title")
                    pr_body = pr_data.get("body")
                    pr_created = pr_data.get("created_at")

                    # Validate URL host/structure
                    expected_prefix = f"https://github.com/{owner}/{repo}/pull/"
                    if pr_url and pr_url.startswith(expected_prefix):
                        return GitPullRequestResult(
                            status=GitPullRequestStatusEnum.ALREADY_EXISTS,
                            pr_number=pr_num,
                            pr_url=pr_url,
                            title=pr_title,
                            body=pr_body,
                            head_branch=head_branch,
                            base_branch=base_branch,
                            created_at=pr_created,
                            message=f"Reconciled existing open Pull Request #{pr_num}",
                        )
        except Exception as exc:
            logger.warning("github_find_existing_pr_failed", error=str(exc))

        return None

    async def verify_remote_branch(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        expected_commit_sha: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Verify that the remote branch exists on GitHub and points to expected commit SHA."""
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch_name}"
        headers = self._get_headers(token)

        try:
            if self._http_client:
                resp = await self._http_client.get(url, headers=headers, timeout=10.0)
            else:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, headers=headers, timeout=10.0)

            if resp.status_code == 200:
                data = resp.json()
                sha = data.get("sha")
                if expected_commit_sha and sha != expected_commit_sha:
                    return False, f"Remote branch commit {sha} does not match expected {expected_commit_sha}"
                return True, sha
            elif resp.status_code == 404:
                return False, f"Remote branch '{branch_name}' does not exist on GitHub"
            else:
                return False, f"GitHub branch verification returned status {resp.status_code}"
        except Exception as exc:
            return False, f"Error verifying remote branch: {str(exc)}"

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        head_branch: str,
        base_branch: str,
        title: str,
        body: str,
        token: Optional[str] = None,
    ) -> GitPullRequestResult:
        """Create a new GitHub Pull Request from head_branch into base_branch.

        Parameters
        ----------
        owner : str
            Repository owner on GitHub.
        repo : str
            Repository name on GitHub.
        head_branch : str
            Source branch containing the fix.
        base_branch : str
            Target default branch to merge into.
        title : str
            Sanitized deterministic PR title.
        body : str
            Sanitized deterministic PR description.
        token : Optional[str]
            GitHub PAT or OAuth token.

        Returns
        -------
        GitPullRequestResult
        """
        # 1. First check if open PR already exists for idempotency reconciliation
        existing_pr = await self.find_existing_pull_request(
            owner=owner,
            repo=repo,
            head_branch=head_branch,
            base_branch=base_branch,
            token=token,
        )
        if existing_pr:
            return existing_pr

        # 2. Build request payload
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        payload = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
        }
        headers = self._get_headers(token)

        try:
            if self._http_client:
                resp = await self._http_client.post(url, json=payload, headers=headers, timeout=10.0)
            else:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, json=payload, headers=headers, timeout=10.0)

            # 3. Classify response
            if resp.status_code == 201:
                data = resp.json()
                pr_num = data.get("number")
                pr_url = data.get("html_url")
                created_at = data.get("created_at") or datetime.now(timezone.utc).isoformat()

                # Validate URL structure (ensure safe GitHub URL)
                expected_prefix = f"https://github.com/{owner}/{repo}/pull/"
                if not pr_url or not pr_url.startswith(expected_prefix):
                    pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_num}"

                return GitPullRequestResult(
                    status=GitPullRequestStatusEnum.CREATED,
                    pr_number=pr_num,
                    pr_url=pr_url,
                    title=title,
                    body=body,
                    head_branch=head_branch,
                    base_branch=base_branch,
                    created_at=created_at,
                    message=f"Successfully created Pull Request #{pr_num}",
                )

            elif resp.status_code == 401:
                return GitPullRequestResult(
                    status=GitPullRequestStatusEnum.AUTH_REQUIRED,
                    head_branch=head_branch,
                    base_branch=base_branch,
                    message="GitHub authentication required — check repository access token",
                    error_details="HTTP 401 Unauthorized",
                )

            elif resp.status_code == 403:
                is_rate_limit = (
                    resp.headers.get("x-ratelimit-remaining") == "0"
                    or "rate limit" in resp.text.lower()
                )
                if is_rate_limit:
                    return GitPullRequestResult(
                        status=GitPullRequestStatusEnum.RATE_LIMITED,
                        head_branch=head_branch,
                        base_branch=base_branch,
                        message="GitHub API rate limit exceeded. Please try again later.",
                        error_details="HTTP 403 Rate Limit Exceeded",
                    )
                return GitPullRequestResult(
                    status=GitPullRequestStatusEnum.PERMISSION_DENIED,
                    head_branch=head_branch,
                    base_branch=base_branch,
                    message="Permission denied creating Pull Request on GitHub repository",
                    error_details=self._mask_error(resp.text),
                )

            elif resp.status_code == 404:
                return GitPullRequestResult(
                    status=GitPullRequestStatusEnum.UNAVAILABLE,
                    head_branch=head_branch,
                    base_branch=base_branch,
                    message=f"GitHub repository {owner}/{repo} not found or inaccessible",
                    error_details="HTTP 404 Not Found",
                )

            elif resp.status_code == 422:
                resp_text = resp.text.lower()
                if "pull request already exists" in resp_text or "already exists" in resp_text:
                    # Re-attempt finding the existing PR
                    found = await self.find_existing_pull_request(
                        owner=owner, repo=repo, head_branch=head_branch, base_branch=base_branch, token=token
                    )
                    if found:
                        return found
                    return GitPullRequestResult(
                        status=GitPullRequestStatusEnum.ALREADY_EXISTS,
                        head_branch=head_branch,
                        base_branch=base_branch,
                        message="A Pull Request for this branch already exists on GitHub",
                        error_details=self._mask_error(resp.text),
                    )
                elif "head" in resp_text or "branch" in resp_text:
                    return GitPullRequestResult(
                        status=GitPullRequestStatusEnum.REMOTE_BRANCH_MISSING,
                        head_branch=head_branch,
                        base_branch=base_branch,
                        message=f"Remote branch '{head_branch}' not found on GitHub",
                        error_details=self._mask_error(resp.text),
                    )
                else:
                    return GitPullRequestResult(
                        status=GitPullRequestStatusEnum.FAILED,
                        head_branch=head_branch,
                        base_branch=base_branch,
                        message="GitHub validation failed for Pull Request creation",
                        error_details=self._mask_error(resp.text),
                    )

            elif resp.status_code == 429:
                return GitPullRequestResult(
                    status=GitPullRequestStatusEnum.RATE_LIMITED,
                    head_branch=head_branch,
                    base_branch=base_branch,
                    message="GitHub API rate limit exceeded",
                    error_details="HTTP 429 Too Many Requests",
                )

            else:
                return GitPullRequestResult(
                    status=GitPullRequestStatusEnum.UNAVAILABLE,
                    head_branch=head_branch,
                    base_branch=base_branch,
                    message="GitHub API returned an unexpected error",
                    error_details=f"HTTP {resp.status_code}: {self._mask_error(resp.text)}",
                )

        except httpx.TimeoutException:
            return GitPullRequestResult(
                status=GitPullRequestStatusEnum.UNAVAILABLE,
                head_branch=head_branch,
                base_branch=base_branch,
                message="GitHub API request timed out",
                error_details="Request timeout",
            )
        except httpx.RequestError as exc:
            return GitPullRequestResult(
                status=GitPullRequestStatusEnum.UNAVAILABLE,
                head_branch=head_branch,
                base_branch=base_branch,
                message="Network error communicating with GitHub API",
                error_details=self._mask_error(str(exc)),
            )
        except Exception as exc:
            return GitPullRequestResult(
                status=GitPullRequestStatusEnum.FAILED,
                head_branch=head_branch,
                base_branch=base_branch,
                message="Unexpected error creating Pull Request",
                error_details=self._mask_error(str(exc)),
            )
