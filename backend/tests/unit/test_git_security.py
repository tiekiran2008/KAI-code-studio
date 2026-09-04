"""
Security Tests — Git Infrastructure & Commit Safety
===================================================
Enforces zero shell execution, prohibits destructive/push commands,
validates branch sanitization, and performs static code audits.
"""
from pathlib import Path
import pytest

from src.infrastructure.git.git_runner import GitCommandRunner, GitExecutionError
from src.infrastructure.git.working_tree_manager import GitWorkingTreeManager


class TestGitSecurity:

    def test_git_runner_prohibits_push(self, tmp_path):
        """GitCommandRunner strictly forbids 'push'."""
        runner = GitCommandRunner()
        with pytest.raises(GitExecutionError, match="Prohibited git subcommand: 'push'"):
            runner.run(["push", "origin", "main"], cwd=tmp_path)

    def test_git_runner_prohibits_rebase(self, tmp_path):
        runner = GitCommandRunner()
        with pytest.raises(GitExecutionError, match="Prohibited git subcommand: 'rebase'"):
            runner.run(["rebase", "main"], cwd=tmp_path)

    def test_git_runner_prohibits_merge(self, tmp_path):
        runner = GitCommandRunner()
        with pytest.raises(GitExecutionError, match="Prohibited git subcommand: 'merge'"):
            runner.run(["merge", "dev"], cwd=tmp_path)

    def test_git_runner_prohibits_force_flag(self, tmp_path):
        runner = GitCommandRunner()
        with pytest.raises(GitExecutionError, match="Prohibited git flag detected: '--force'"):
            runner.run(["checkout", "--force", "main"], cwd=tmp_path)

    def test_git_runner_prohibits_hard_reset(self, tmp_path):
        runner = GitCommandRunner()
        with pytest.raises(GitExecutionError, match="Prohibited git flag detected: '--hard'"):
            runner.run(["reset", "--hard", "HEAD~1"], cwd=tmp_path)

    def test_git_runner_prohibits_clean_force(self, tmp_path):
        runner = GitCommandRunner()
        with pytest.raises(GitExecutionError, match="Prohibited git flag detected: '-fd'"):
            runner.run(["clean", "-fd"], cwd=tmp_path)

    def test_git_runner_zero_shell_execution(self, tmp_path):
        """GitCommandRunner executes via subprocess list (shell=False); shell injections fail."""
        runner = GitCommandRunner()
        with pytest.raises(Exception):
            runner.run(["status; echo INJECTED"], cwd=tmp_path)

    def test_branch_name_sanitization(self):
        """Branch name validator strictly rejects shell metacharacters and directory traversal."""
        manager = GitWorkingTreeManager()

        malicious_branches = [
            "; rm -rf /",
            "$(whoami)",
            "`id`",
            "branch|cat",
            "../../escaped",
            "-f",
            "--force",
            "refs/heads/main",
            "branch name with space",
            "head~1",
            "head^2",
            "head:file",
            "head?glob",
            "head*star",
            "head[0-9]",
        ]

        for b in malicious_branches:
            assert manager.validate_branch_name(b) is False, f"Expected '{b}' to be rejected as branch name"

    def test_static_code_security_audit(self):
        """Audit codebase files for prohibited Git patterns."""
        target_files = [
            Path("src/infrastructure/git/git_runner.py"),
            Path("src/infrastructure/git/working_tree_manager.py"),
            Path("src/application/use_cases/commit_applied_fix.py"),
        ]

        prohibited_literals = [
            "shell=True",
            "git add .",
            "git add -A",
            "git commit -a",
            "reset --hard",
            "clean -fd",
            "checkout -- .",
            "restore .",
            "os.system",
        ]

        backend_root = Path(__file__).resolve().parent.parent.parent

        for rel_path in target_files:
            file_path = backend_root / rel_path
            assert file_path.exists(), f"File {file_path} must exist"
            content = file_path.read_text(encoding="utf-8")

            for literal in prohibited_literals:
                assert literal not in content, (
                    f"Security violation: found prohibited literal '{literal}' in {rel_path}"
                )
