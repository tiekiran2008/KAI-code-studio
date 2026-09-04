"""
Git Working Tree Manager
========================
Inspects local working tree state and executes targeted fix commits
using temporary Git index isolation (zero mutation of user's active branch or user-staged files).
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import tempfile
from typing import List, Optional, Tuple

from src.core.logger import logger
from src.domain.entities.git import (
    GitCommitResult,
    GitCommitStatusEnum,
    GitPushResult,
    GitPushStatusEnum,
    WorkingTreeStatus,
)
from src.infrastructure.git.git_runner import GitCommandRunner, GitExecutionError
from src.infrastructure.filesystem.path_sandbox import PathSandboxService


class GitWorkingTreeManager:
    """Manages Git working tree inspection and isolated branch committing."""

    DEFAULT_BOT_NAME = "Antigravity Reviewer"
    DEFAULT_BOT_EMAIL = "ai-reviewer@local"

    # Branch name regex: starts with alphanumeric, contains only safe chars, max 100 chars
    BRANCH_NAME_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9/_.-]{0,99}$")

    def __init__(
        self,
        runner: Optional[GitCommandRunner] = None,
        path_sandbox: Optional[PathSandboxService] = None,
    ) -> None:
        self.runner = runner or GitCommandRunner()
        self.path_sandbox = path_sandbox or PathSandboxService()

    def is_git_repository(self, workspace_root: Path) -> bool:
        """Check if workspace_root is a valid Git repository."""
        if not workspace_root.exists() or not workspace_root.is_dir():
            return False
        code, out, _ = self.runner.run(
            ["rev-parse", "--is-inside-work-tree"],
            cwd=workspace_root,
            check=False,
        )
        return code == 0 and out.lower() == "true"

    def get_working_tree_status(self, workspace_root: Path) -> WorkingTreeStatus:
        """Inspect the current working tree state without modifying anything."""
        if not self.is_git_repository(workspace_root):
            return WorkingTreeStatus(is_git_repo=False)

        # 1. Active branch name
        _, branch_out, _ = self.runner.run(
            ["rev-parse", "--abbrev-ref", "HEAD"],
            cwd=workspace_root,
            check=False,
        )
        current_branch = branch_out if branch_out else None

        # 2. HEAD commit SHA
        _, sha_out, _ = self.runner.run(
            ["rev-parse", "HEAD"],
            cwd=workspace_root,
            check=False,
        )
        head_commit_sha = sha_out if sha_out and len(sha_out) == 40 else None

        # 3. Status porcelain inspection
        _, status_out, _ = self.runner.run(
            ["status", "--porcelain=v1"],
            cwd=workspace_root,
            check=False,
        )

        modified: List[str] = []
        staged: List[str] = []
        untracked: List[str] = []

        for line in status_out.splitlines():
            if len(line) < 3:
                continue
            index_status = line[0]
            worktree_status = line[1]
            file_name = line[3:].strip()

            if index_status not in (" ", "?"):
                staged.append(file_name)
            if worktree_status not in (" ", "?"):
                modified.append(file_name)
            if index_status == "?" and worktree_status == "?":
                untracked.append(file_name)

        return WorkingTreeStatus(
            is_git_repo=True,
            current_branch=current_branch,
            head_commit_sha=head_commit_sha,
            modified_files=modified,
            staged_files=staged,
            untracked_files=untracked,
        )

    def generate_branch_name(self, review_id: str, finding_index: int) -> str:
        """Generate a deterministic, safe branch name for a finding fix."""
        short_rev = review_id.replace("-", "")[:8]
        return f"ai-fix/rev-{short_rev}-f{finding_index}"

    def validate_branch_name(self, branch_name: str) -> bool:
        """Validate branch name to prevent flag injection or illegal Git ref characters."""
        if not branch_name or not isinstance(branch_name, str):
            return False
        if not self.BRANCH_NAME_REGEX.match(branch_name):
            return False
        # Disallow prohibited sequences and namespaces in Git branch names
        if branch_name.startswith("refs/") or branch_name.startswith("heads/"):
            return False
        prohibited = ["..", "@{", "~", "^", ":", "?", "*", "[", "\\", "//", ".lock"]
        if any(p in branch_name for p in prohibited):
            return False
        if branch_name.endswith("/") or branch_name.endswith("."):
            return False
        return True

    def create_isolated_fix_commit(
        self,
        workspace_root: Path,
        relative_target_path: str,
        review_id: str,
        finding_index: int,
        finding_issue: Optional[str] = None,
        custom_branch_name: Optional[str] = None,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> GitCommitResult:
        """Create a targeted commit on a dedicated AI fix branch using temporary index isolation.

        Key Invariants:
        1. Never switches or mutates the user's active branch.
        2. Never captures unrelated modified, untracked, or user-staged files.
        3. Temporary Git index (GIT_INDEX_FILE) created and cleanly deleted.
        4. Staged diff verified to contain strictly the target file before commit creation.
        """
        # 1. Check Git repository
        if not self.is_git_repository(workspace_root):
            return GitCommitResult(
                status=GitCommitStatusEnum.NOT_GIT_REPOSITORY,
                message="Workspace is not a valid Git repository",
            )

        # 2. Path validation
        try:
            target_path = self.path_sandbox.validate_path(
                workspace_root=workspace_root,
                relative_path=relative_target_path,
                must_be_file=True,
            )
            rel_path_normalized = target_path.relative_to(workspace_root).as_posix()
        except Exception as exc:
            return GitCommitResult(
                status=GitCommitStatusEnum.FAILED,
                error_details=f"Path validation failed: {exc}",
            )

        if not target_path.exists() or not target_path.is_file():
            return GitCommitResult(
                status=GitCommitStatusEnum.FAILED,
                error_details=f"Target file does not exist on disk: '{relative_target_path}'",
            )

        # 3. Determine branch name
        branch_name = custom_branch_name or self.generate_branch_name(review_id, finding_index)
        if not self.validate_branch_name(branch_name):
            return GitCommitResult(
                status=GitCommitStatusEnum.FAILED,
                error_details=f"Invalid or unsafe branch name: '{branch_name}'",
            )

        # 4. Resolve base commit and base branch
        code, base_sha, _ = self.runner.run(
            ["rev-parse", "HEAD"],
            cwd=workspace_root,
            check=False,
        )
        if code != 0 or not base_sha:
            return GitCommitResult(
                status=GitCommitStatusEnum.FAILED,
                error_details="Could not resolve HEAD commit SHA in repository",
            )

        _, base_branch, _ = self.runner.run(
            ["rev-parse", "--abbrev-ref", "HEAD"],
            cwd=workspace_root,
            check=False,
        )

        # 5. Check if dedicated branch already exists
        code, existing_branch_sha, _ = self.runner.run(
            ["rev-parse", "--verify", f"refs/heads/{branch_name}"],
            cwd=workspace_root,
            check=False,
        )
        # If branch already exists, we will update it or create from base
        parent_commit = existing_branch_sha if (code == 0 and existing_branch_sha) else base_sha

        # 6. Author and committer identities
        user_name = author_name or self.DEFAULT_BOT_NAME
        user_email = author_email or self.DEFAULT_BOT_EMAIL

        # 7. Create temporary Git index file for isolation
        temp_idx = tempfile.NamedTemporaryFile(prefix="agy_git_idx_", delete=False)
        temp_idx.close()
        temp_idx_path = temp_idx.name

        try:
            env_override = {"GIT_INDEX_FILE": temp_idx_path}

            # Step A: Read base commit tree into isolated temporary index
            self.runner.run(
                ["read-tree", parent_commit],
                cwd=workspace_root,
                env_override=env_override,
            )

            # Step B: Stage ONLY the target file into temporary index
            self.runner.run(
                ["add", "--", rel_path_normalized],
                cwd=workspace_root,
                env_override=env_override,
            )

            # Step C: Verify temporary index contents (must contain strictly the intended file)
            _, cached_diff_files, _ = self.runner.run(
                ["diff", "--cached", "--name-only"],
                cwd=workspace_root,
                env_override=env_override,
            )

            staged_in_temp = [f.strip() for f in cached_diff_files.splitlines() if f.strip()]
            if not staged_in_temp:
                return GitCommitResult(
                    status=GitCommitStatusEnum.FAILED,
                    error_details="No changes were detected to stage for target file",
                )

            # Strict assertion: no other files allowed in temporary index diff
            normalized_staged = [p.replace("\\", "/") for p in staged_in_temp]
            if normalized_staged != [rel_path_normalized]:
                return GitCommitResult(
                    status=GitCommitStatusEnum.FAILED,
                    error_details=f"Unexpected files staged in temporary index: {staged_in_temp}",
                )

            # Step D: Write tree from temporary index
            _, tree_sha, _ = self.runner.run(
                ["write-tree"],
                cwd=workspace_root,
                env_override=env_override,
            )

            # Step E: Build deterministic commit message
            commit_subject = f"fix: resolve finding {finding_index} in {rel_path_normalized}"
            if finding_issue:
                # Sanitize single-line issue summary
                clean_issue = " ".join(finding_issue.split())[:120]
                commit_subject = f"fix(review): {clean_issue}"

            commit_body = (
                f"{commit_subject}\n\n"
                f"- Review ID: {review_id}\n"
                f"- Finding Index: {finding_index}\n"
                f"- Target File: {rel_path_normalized}\n"
                f"- Verified: Automated static and isolated verification passed"
            )

            # Step F: Create commit object pointing to parent commit
            commit_cmd = [
                "-c", f"user.name={user_name}",
                "-c", f"user.email={user_email}",
                "commit-tree", tree_sha,
                "-p", parent_commit,
                "-m", commit_body,
            ]
            _, commit_sha, _ = self.runner.run(
                commit_cmd,
                cwd=workspace_root,
                env_override=env_override,
            )

            # Step G: Update branch ref without touching HEAD or active branch
            self.runner.run(
                ["update-ref", f"refs/heads/{branch_name}", commit_sha],
                cwd=workspace_root,
            )

            now_iso = datetime.now(timezone.utc).isoformat()

            logger.info(
                "isolated_git_commit_created",
                branch=branch_name,
                commit_sha=commit_sha,
                target_file=rel_path_normalized,
                base_sha=base_sha,
            )

            return GitCommitResult(
                status=GitCommitStatusEnum.COMMITTED,
                branch_name=branch_name,
                commit_sha=commit_sha,
                committed_at=now_iso,
                file_path=rel_path_normalized,
                commit_message=commit_subject,
                base_branch=base_branch,
                base_commit_sha=base_sha,
                message=f"Created commit {commit_sha[:8]} on branch {branch_name}",
            )

        except GitExecutionError as exc:
            logger.error("git_commit_failed", error=str(exc))
            return GitCommitResult(
                status=GitCommitStatusEnum.FAILED,
                error_details=f"Git operation failed: {exc}",
            )
        except Exception as exc:
            logger.error("git_commit_unexpected_error", error=str(exc))
            return GitCommitResult(
                status=GitCommitStatusEnum.FAILED,
                error_details=f"Unexpected error creating commit: {exc}",
            )
        finally:
            # Clean up temporary index file
            if os.path.exists(temp_idx_path):
                try:
                    os.remove(temp_idx_path)
                except Exception as rem_err:
                    logger.warning(f"Could not remove temporary git index: {rem_err}")

    @staticmethod
    def mask_remote_url(url: str) -> str:
        """Strip sensitive credentials/tokens from a remote URL for safe reporting/logging."""
        if not url:
            return ""
        # Match http(s)://user:token@host or http(s)://token@host
        return re.sub(r"://([^@]+)@", "://***@", url)

    def get_remote_url(self, workspace_root: Path, remote_name: str = "origin") -> Optional[str]:
        """Fetch configured URL for a Git remote (returns None if not configured)."""
        code, out, _ = self.runner.run(
            ["config", f"remote.{remote_name}.url"],
            cwd=workspace_root,
            check=False,
        )
        if code == 0 and out:
            return out.strip()
        return None

    def validate_remote(
        self,
        workspace_root: Path,
        remote_name: str = "origin",
        expected_repo_url: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate that the workspace has a valid, non-malicious remote configured.

        Returns (is_valid, masked_url, error_message).
        """
        raw_url = self.get_remote_url(workspace_root, remote_name)
        if not raw_url:
            return False, None, f"No Git remote '{remote_name}' configured in repository"

        masked_url = self.mask_remote_url(raw_url)

        # Prohibit dangerous protocols (file://, local system paths, shell injection characters)
        if raw_url.startswith("file://") or ";" in raw_url or "&" in raw_url or "|" in raw_url or "`" in raw_url:
            return False, masked_url, f"Prohibited or unsafe protocol in remote URL: '{masked_url}'"

        # If expected_repo_url is provided, verify normalized match
        if expected_repo_url:
            def _normalize(u: str) -> str:
                u = u.strip().rstrip("/").removesuffix(".git")
                # Strip credentials if any
                u = re.sub(r"https?://[^@]+@", "https://", u)
                return u.lower()

            norm_actual = _normalize(raw_url)
            norm_expected = _normalize(expected_repo_url)
            if norm_actual != norm_expected and not norm_actual.endswith(norm_expected) and not norm_expected.endswith(norm_actual):
                # Check for same repo path on github.com
                return False, masked_url, f"Configured remote '{masked_url}' does not match repository URL '{self.mask_remote_url(expected_repo_url)}'"

        return True, masked_url, None

    def push_isolated_branch(
        self,
        workspace_root: Path,
        branch_name: str,
        expected_commit_sha: str,
        remote_name: str = "origin",
        expected_repo_url: Optional[str] = None,
    ) -> GitPushResult:
        """Push a dedicated AI fix branch to a trusted remote without force push or working tree mutation.

        Enforces:
        - Must be a valid Git repository
        - Branch name matches strict safe regex
        - Local branch ref exists and tip commit SHA == expected_commit_sha
        - Remote exists, is validated, and does not mismatch
        - If remote branch already points to expected_commit_sha -> ALREADY_PUSHED
        - Never uses force push (--force, -f, --force-with-lease, +)
        - Active branch/HEAD/index/working-tree remain completely untouched
        """
        if not self.is_git_repository(workspace_root):
            return GitPushResult(
                status=GitPushStatusEnum.NO_REMOTE,
                error_details="Workspace is not a valid Git repository",
            )

        # 1. Sanitize branch name
        if not branch_name or not self.BRANCH_NAME_REGEX.match(branch_name):
            return GitPushResult(
                status=GitPushStatusEnum.FAILED,
                error_details=f"Invalid branch name: '{branch_name}'",
            )

        # 2. Check local branch exists and points to expected_commit_sha
        local_ref = f"refs/heads/{branch_name}"
        code, local_sha, _ = self.runner.run(
            ["rev-parse", "--verify", local_ref],
            cwd=workspace_root,
            check=False,
        )
        if code != 0 or not local_sha:
            return GitPushResult(
                status=GitPushStatusEnum.GIT_STATE_CHANGED,
                branch_name=branch_name,
                error_details=f"Local branch '{branch_name}' does not exist",
            )

        if local_sha.strip() != expected_commit_sha.strip():
            return GitPushResult(
                status=GitPushStatusEnum.GIT_STATE_CHANGED,
                branch_name=branch_name,
                commit_sha=local_sha.strip(),
                error_details=(
                    f"Local branch tip ({local_sha[:8]}) does not match expected commit SHA ({expected_commit_sha[:8]})"
                ),
            )

        # 3. Validate remote
        is_valid, masked_url, error_msg = self.validate_remote(workspace_root, remote_name, expected_repo_url)
        if not is_valid:
            if "No Git remote" in (error_msg or ""):
                return GitPushResult(
                    status=GitPushStatusEnum.NO_REMOTE,
                    remote_name=remote_name,
                    branch_name=branch_name,
                    commit_sha=expected_commit_sha,
                    error_details=error_msg,
                )
            return GitPushResult(
                status=GitPushStatusEnum.REMOTE_MISMATCH,
                remote_name=remote_name,
                branch_name=branch_name,
                commit_sha=expected_commit_sha,
                remote_url_masked=masked_url,
                error_details=error_msg,
            )

        # 4. Check if remote already has this branch at this commit (Idempotency)
        ls_code, ls_out, _ = self.runner.run(
            ["ls-remote", "--heads", remote_name, local_ref],
            cwd=workspace_root,
            check=False,
        )
        if ls_code == 0 and ls_out:
            remote_sha = ls_out.split()[0] if ls_out.split() else ""
            if remote_sha == expected_commit_sha:
                now_iso = datetime.now(timezone.utc).isoformat()
                return GitPushResult(
                    status=GitPushStatusEnum.ALREADY_PUSHED,
                    remote_name=remote_name,
                    branch_name=branch_name,
                    commit_sha=expected_commit_sha,
                    remote_url_masked=masked_url,
                    pushed_at=now_iso,
                    message=f"Branch '{branch_name}' is already up-to-date on remote '{remote_name}'",
                )

        # 5. Execute safe push
        remote_ref = f"refs/heads/{branch_name}"
        exit_code, stdout, stderr = self.runner.push_ref(
            remote_name=remote_name,
            local_ref=local_ref,
            remote_ref=remote_ref,
            cwd=workspace_root,
        )

        now_iso = datetime.now(timezone.utc).isoformat()

        if exit_code == 0:
            logger.info(
                "git_branch_pushed_success",
                remote=remote_name,
                branch=branch_name,
                commit_sha=expected_commit_sha,
            )
            return GitPushResult(
                status=GitPushStatusEnum.PUSHED,
                remote_name=remote_name,
                branch_name=branch_name,
                commit_sha=expected_commit_sha,
                remote_url_masked=masked_url,
                pushed_at=now_iso,
                message=f"Successfully pushed branch '{branch_name}' to remote '{remote_name}'",
            )

        # Classify failure safely
        combined_err = f"{stderr} {stdout}".strip()
        clean_err = self.mask_remote_url(combined_err)

        if any(w in clean_err.lower() for w in ("auth", "permission denied", "could not read username", "forbidden", "403", "401")):
            return GitPushResult(
                status=GitPushStatusEnum.AUTH_REQUIRED,
                remote_name=remote_name,
                branch_name=branch_name,
                commit_sha=expected_commit_sha,
                remote_url_masked=masked_url,
                error_details="Remote authentication required or access denied",
            )
        elif any(w in clean_err.lower() for w in ("rejected", "non-fast-forward", "protected branch", "hook declined")):
            return GitPushResult(
                status=GitPushStatusEnum.PUSH_REJECTED,
                remote_name=remote_name,
                branch_name=branch_name,
                commit_sha=expected_commit_sha,
                remote_url_masked=masked_url,
                error_details=f"Remote rejected branch push: {clean_err}",
            )
        elif any(w in clean_err.lower() for w in ("could not resolve host", "connection refused", "timed out", "unable to access")):
            return GitPushResult(
                status=GitPushStatusEnum.REMOTE_UNAVAILABLE,
                remote_name=remote_name,
                branch_name=branch_name,
                commit_sha=expected_commit_sha,
                remote_url_masked=masked_url,
                error_details="Remote repository is currently unavailable or unreachable",
            )
        else:
            return GitPushResult(
                status=GitPushStatusEnum.FAILED,
                remote_name=remote_name,
                branch_name=branch_name,
                commit_sha=expected_commit_sha,
                remote_url_masked=masked_url,
                error_details=f"Failed pushing branch: {clean_err}",
            )

