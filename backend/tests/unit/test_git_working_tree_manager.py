"""
Unit Tests — GitWorkingTreeManager
==================================
Validates working tree inspection, branch name generation & sanitization,
targeted single-file staging, temporary index isolation, and unrelated
working tree / staging preservation.
"""
from pathlib import Path
import subprocess
import tempfile
import pytest

from src.domain.entities.git import GitCommitStatusEnum
from src.infrastructure.git.working_tree_manager import GitWorkingTreeManager
from src.infrastructure.git.git_runner import GitCommandRunner


def _init_git_repo(path: Path) -> None:
    """Helper to initialize a real git repository with an initial commit."""
    subprocess.run(["git", "init"], cwd=str(path), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "--allow-empty", "-m", "Initial commit"],
        cwd=str(path),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class TestGitWorkingTreeManager:

    def test_non_git_repository_detected(self, tmp_path):
        """Non-git folder returns is_git_repo=False."""
        manager = GitWorkingTreeManager()
        status = manager.get_working_tree_status(tmp_path)
        assert status.is_git_repo is False
        assert not manager.is_git_repository(tmp_path)

    def test_working_tree_status_inspection(self, tmp_path):
        """Detects modified, staged, and untracked files accurately."""
        _init_git_repo(tmp_path)
        manager = GitWorkingTreeManager()

        # Create tracked file
        f1 = tmp_path / "tracked.txt"
        f1.write_text("v1\n")
        subprocess.run(["git", "add", "tracked.txt"], cwd=str(tmp_path), check=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "add tracked"],
            cwd=str(tmp_path),
            check=True,
        )

        # 1. Modify tracked file (unstaged)
        f1.write_text("v2 modified\n")

        # 2. Create staged file
        f2 = tmp_path / "staged.txt"
        f2.write_text("staged content\n")
        subprocess.run(["git", "add", "staged.txt"], cwd=str(tmp_path), check=True)

        # 3. Create untracked file
        f3 = tmp_path / "untracked.txt"
        f3.write_text("untracked content\n")

        status = manager.get_working_tree_status(tmp_path)
        assert status.is_git_repo is True
        assert "tracked.txt" in status.modified_files
        assert "staged.txt" in status.staged_files
        assert "untracked.txt" in status.untracked_files

    def test_branch_name_sanitization_and_rejection(self):
        """Validates branch name rules and rejects injection patterns."""
        manager = GitWorkingTreeManager()

        # Valid names
        assert manager.validate_branch_name("ai-fix/rev-12345678-f0") is True
        assert manager.validate_branch_name("feature/bug-fix_1.0") is True

        # Invalid / injection names
        assert manager.validate_branch_name("-flag-injection") is False
        assert manager.validate_branch_name("branch with spaces") is False
        assert manager.validate_branch_name("branch..traversal") is False
        assert manager.validate_branch_name("branch~1") is False
        assert manager.validate_branch_name("branch^2") is False
        assert manager.validate_branch_name("branch:colon") is False
        assert manager.validate_branch_name("branch?wildcard") is False
        assert manager.validate_branch_name("branch*asterisk") is False
        assert manager.validate_branch_name("branch[bracket]") is False
        assert manager.validate_branch_name("branch\\backslash") is False
        assert manager.validate_branch_name("branch/trailing/") is False

    def test_clean_repo_isolated_commit_creation(self, tmp_path):
        """Creates commit on dedicated branch without modifying HEAD or active branch."""
        _init_git_repo(tmp_path)
        manager = GitWorkingTreeManager()

        # Initial source file
        src_file = tmp_path / "src" / "calc.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("def add(a, b):\n    return a + b\n")
        subprocess.run(["git", "add", "src/calc.py"], cwd=str(tmp_path), check=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "add calc"],
            cwd=str(tmp_path),
            check=True,
        )

        # Apply fix on disk
        src_file.write_text("def add(a: int, b: int) -> int:\n    return a + b\n")

        # Create isolated commit
        result = manager.create_isolated_fix_commit(
            workspace_root=tmp_path,
            relative_target_path="src/calc.py",
            review_id="rev-12345678-abcd",
            finding_index=0,
            finding_issue="Missing type hints",
        )

        assert result.status == GitCommitStatusEnum.COMMITTED
        assert result.commit_sha is not None
        assert len(result.commit_sha) == 40
        assert result.branch_name == "ai-fix/rev-rev12345-f0"

        # Verify active branch HEAD has NOT changed
        active_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(tmp_path),
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        assert active_branch in ("main", "master")

        # Verify commit content on the dedicated branch
        diff_output = subprocess.run(
            ["git", "diff", f"{result.base_commit_sha}..{result.commit_sha}", "--name-only"],
            cwd=str(tmp_path),
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        assert diff_output == "src/calc.py"

    def test_unrelated_modified_files_are_not_committed(self, tmp_path):
        """CRITICAL: User's modified fileB is NOT included in the AI commit."""
        _init_git_repo(tmp_path)
        manager = GitWorkingTreeManager()

        # Create fileA and fileB
        file_a = tmp_path / "fileA.py"
        file_b = tmp_path / "fileB.py"
        file_a.write_text("file A original\n")
        file_b.write_text("file B original\n")
        subprocess.run(["git", "add", "fileA.py", "fileB.py"], cwd=str(tmp_path), check=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "init A and B"],
            cwd=str(tmp_path),
            check=True,
        )

        # AI fix modifies fileA; user modifies fileB
        file_a.write_text("file A fixed\n")
        file_b.write_text("file B user modifications\n")

        result = manager.create_isolated_fix_commit(
            workspace_root=tmp_path,
            relative_target_path="fileA.py",
            review_id="rev-test-1",
            finding_index=0,
        )

        assert result.status == GitCommitStatusEnum.COMMITTED

        # Verify commit contains strictly fileA.py
        diff_files = subprocess.run(
            ["git", "diff", f"{result.base_commit_sha}..{result.commit_sha}", "--name-only"],
            cwd=str(tmp_path),
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        assert diff_files == "fileA.py"

        # Verify user's working tree fileB is still modified
        assert file_b.read_text() == "file B user modifications\n"
        status = manager.get_working_tree_status(tmp_path)
        assert "fileB.py" in status.modified_files

    def test_user_staged_changes_preserved_in_index(self, tmp_path):
        """CRITICAL: User's staged fileC remains staged in primary .git/index after AI commit."""
        _init_git_repo(tmp_path)
        manager = GitWorkingTreeManager()

        # Create fileA and fileC
        file_a = tmp_path / "fileA.py"
        file_c = tmp_path / "fileC.py"
        file_a.write_text("file A base\n")
        file_c.write_text("file C base\n")
        subprocess.run(["git", "add", "fileA.py", "fileC.py"], cwd=str(tmp_path), check=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "init A and C"],
            cwd=str(tmp_path),
            check=True,
        )

        # User modifies and stages fileC
        file_c.write_text("file C user staged work\n")
        subprocess.run(["git", "add", "fileC.py"], cwd=str(tmp_path), check=True)

        # AI fix modifies fileA
        file_a.write_text("file A applied fix\n")

        result = manager.create_isolated_fix_commit(
            workspace_root=tmp_path,
            relative_target_path="fileA.py",
            review_id="rev-test-2",
            finding_index=0,
        )

        assert result.status == GitCommitStatusEnum.COMMITTED

        # Verify commit contains strictly fileA.py
        diff_files = subprocess.run(
            ["git", "diff", f"{result.base_commit_sha}..{result.commit_sha}", "--name-only"],
            cwd=str(tmp_path),
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        assert diff_files == "fileA.py"

        # Verify primary index STILL has fileC.py staged
        status = manager.get_working_tree_status(tmp_path)
        assert "fileC.py" in status.staged_files
