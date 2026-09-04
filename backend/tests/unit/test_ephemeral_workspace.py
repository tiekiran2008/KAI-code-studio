"""
Unit Tests — Ephemeral Workspace Manager
========================================
Verifies copy-on-execution, secret file exclusion, path traversal protection,
and cleanup reliability.
"""
from pathlib import Path
import tempfile
import pytest

from src.core.errors import WorkflowExecutionError
from src.infrastructure.sandbox.ephemeral_workspace import EphemeralWorkspaceManager


@pytest.fixture
def sample_repo_dir():
    """Create a temporary repository directory with various files and subdirectories."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_repo_src_"))

    # Regular source files
    (temp_dir / "src").mkdir()
    (temp_dir / "src" / "calculator.py").write_text("def add(a, b):\n    return a + b\n")

    # Tests
    (temp_dir / "tests").mkdir()
    (temp_dir / "tests" / "test_calc.py").write_text("from src.calculator import add\ndef test_add(): assert add(1, 2) == 3\n")

    # Sensitive files that MUST be excluded
    (temp_dir / ".env").write_text("SECRET_KEY=supersecret\n")
    (temp_dir / ".env.local").write_text("DATABASE_PASSWORD=secret123\n")
    (temp_dir / "id_rsa.key").write_text("-----BEGIN PRIVATE KEY-----\n")
    (temp_dir / "cert.pem").write_text("-----BEGIN CERTIFICATE-----\n")

    # Excluded directories
    (temp_dir / ".git").mkdir()
    (temp_dir / ".git" / "config").write_text("[core]\n")
    (temp_dir / ".venv").mkdir()
    (temp_dir / ".venv" / "pip.txt").write_text("virtualenv\n")
    (temp_dir / "node_modules").mkdir()
    (temp_dir / "node_modules" / "dummy.js").write_text("console.log();\n")
    (temp_dir / "__pycache__").mkdir()
    (temp_dir / "__pycache__" / "calc.pyc").write_text("bytecode\n")

    yield temp_dir

    # Cleanup source fixture
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_ephemeral_workspace_copies_source_and_test_files(sample_repo_dir):
    manager = EphemeralWorkspaceManager()
    context = manager.create_snapshot(str(sample_repo_dir))

    try:
        assert context.temp_path.exists()
        assert (context.temp_path / "src" / "calculator.py").exists()
        assert (context.temp_path / "tests" / "test_calc.py").exists()
        assert (context.temp_path / "src" / "calculator.py").read_text() == "def add(a, b):\n    return a + b\n"
    finally:
        context.cleanup()

    assert not context.temp_path.exists()


def test_ephemeral_workspace_excludes_secrets_and_vcs(sample_repo_dir):
    manager = EphemeralWorkspaceManager()
    context = manager.create_snapshot(str(sample_repo_dir))

    try:
        # Excluded sensitive files
        assert not (context.temp_path / ".env").exists()
        assert not (context.temp_path / ".env.local").exists()
        assert not (context.temp_path / "id_rsa.key").exists()
        assert not (context.temp_path / "cert.pem").exists()

        # Excluded directories
        assert not (context.temp_path / ".git").exists()
        assert not (context.temp_path / ".venv").exists()
        assert not (context.temp_path / "node_modules").exists()
        assert not (context.temp_path / "__pycache__").exists()
    finally:
        context.cleanup()


def test_ephemeral_workspace_immutability(sample_repo_dir):
    """Mutating files in the ephemeral workspace copy does NOT affect the original repository."""
    manager = EphemeralWorkspaceManager()
    context = manager.create_snapshot(str(sample_repo_dir))

    try:
        # Mutate file in ephemeral workspace
        mutated_file = context.temp_path / "src" / "calculator.py"
        mutated_file.write_text("def add(a, b): return 99999\n")
        assert mutated_file.read_text() == "def add(a, b): return 99999\n"

        # Create new arbitrary test file in ephemeral workspace
        (context.temp_path / "tests" / "malicious_created.txt").write_text("created in container\n")

        # Verify original source directory remains 100% UNCHANGED
        orig_file = sample_repo_dir / "src" / "calculator.py"
        assert orig_file.read_text() == "def add(a, b):\n    return a + b\n"
        assert not (sample_repo_dir / "tests" / "malicious_created.txt").exists()
    finally:
        context.cleanup()


def test_ephemeral_workspace_rejects_nonexistent_directory():
    manager = EphemeralWorkspaceManager()
    with pytest.raises(WorkflowExecutionError, match="does not exist"):
        manager.create_snapshot("/path/to/nonexistent/repo/root/xyz")
