"""
Unit Tests: Path Sandbox Service
================================
Validates path traversal, symlink escapes, drive letters, UNC paths, and boundaries.
"""
import os
import pytest
from pathlib import Path

from src.infrastructure.filesystem.path_sandbox import PathSandboxService
from src.domain.entities.patch import UnsafePathError, SymlinkEscapeError


@pytest.fixture
def sandbox_env(tmp_path):
    """Create a mock workspace sandbox with sample files and subdirectories."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Subdirectories
    src_dir = workspace / "src"
    src_dir.mkdir()
    nested_dir = src_dir / "utils"
    nested_dir.mkdir()

    # Files
    (src_dir / "main.py").write_text("print('hello')", encoding="utf-8")
    (nested_dir / "math.py").write_text("def add(a, b): return a + b", encoding="utf-8")

    # Outside file
    outside_file = tmp_path / "outside.py"
    outside_file.write_text("secret_data = 123", encoding="utf-8")

    return {
        "root": workspace,
        "outside_file": outside_file,
        "tmp_path": tmp_path,
    }


def test_valid_nested_file_allowed(sandbox_env):
    root = sandbox_env["root"]
    resolved = PathSandboxService.validate_path(root, "src/utils/math.py", must_be_file=True)
    assert resolved.is_file()
    assert resolved == (root / "src" / "utils" / "math.py").resolve()


def test_relative_slash_traversal_blocked(sandbox_env):
    root = sandbox_env["root"]
    with pytest.raises(UnsafePathError, match="traversal"):
        PathSandboxService.validate_path(root, "../outside.py")

    with pytest.raises(UnsafePathError, match="traversal"):
        PathSandboxService.validate_path(root, "src/../../outside.py")


def test_windows_backslash_traversal_blocked(sandbox_env):
    root = sandbox_env["root"]
    with pytest.raises(UnsafePathError, match="traversal"):
        PathSandboxService.validate_path(root, r"..\outside.py")

    with pytest.raises(UnsafePathError, match="traversal"):
        PathSandboxService.validate_path(root, r"src\..\..\outside.py")


def test_absolute_unix_path_blocked(sandbox_env):
    root = sandbox_env["root"]
    with pytest.raises(UnsafePathError, match="Absolute paths are forbidden"):
        PathSandboxService.validate_path(root, "/etc/passwd")


def test_absolute_windows_path_blocked(sandbox_env):
    root = sandbox_env["root"]
    with pytest.raises(UnsafePathError, match="Drive-qualified paths are forbidden|Absolute paths are forbidden"):
        PathSandboxService.validate_path(root, "C:\\Windows\\System32\\cmd.exe")


def test_unc_network_path_blocked(sandbox_env):
    root = sandbox_env["root"]
    with pytest.raises(UnsafePathError, match="UNC network paths are forbidden"):
        PathSandboxService.validate_path(root, r"\\server\share\file.py")

    with pytest.raises(UnsafePathError, match="UNC network paths are forbidden"):
        PathSandboxService.validate_path(root, "//server/share/file.py")


def test_null_byte_path_blocked(sandbox_env):
    root = sandbox_env["root"]
    with pytest.raises(UnsafePathError, match="Null bytes are not allowed"):
        PathSandboxService.validate_path(root, "src/main.py\x00.evil")


def test_empty_or_whitespace_path_blocked(sandbox_env):
    root = sandbox_env["root"]
    with pytest.raises(UnsafePathError, match="cannot be empty"):
        PathSandboxService.validate_path(root, "   ")


def test_root_directory_as_target_rejected(sandbox_env):
    root = sandbox_env["root"]
    with pytest.raises(UnsafePathError, match="cannot be the workspace root"):
        PathSandboxService.validate_path(root, ".")


def test_directory_when_must_be_file_rejected(sandbox_env):
    root = sandbox_env["root"]
    with pytest.raises(UnsafePathError, match="Target path is a directory, not a file"):
        PathSandboxService.validate_path(root, "src", must_be_file=True)


def test_symlink_pointing_outside_blocked(sandbox_env):
    root = sandbox_env["root"]
    outside_file = sandbox_env["outside_file"]

    symlink_path = root / "src" / "escape_link.py"
    try:
        symlink_path.symlink_to(outside_file)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported in current environment/permissions")

    with pytest.raises(SymlinkEscapeError, match="points outside workspace boundary"):
        PathSandboxService.validate_path(root, "src/escape_link.py")


def test_symlink_pointing_inside_allowed(sandbox_env):
    root = sandbox_env["root"]
    target_file = root / "src" / "main.py"

    symlink_path = root / "src" / "safe_link.py"
    try:
        symlink_path.symlink_to(target_file)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported in current environment/permissions")

    resolved = PathSandboxService.validate_path(root, "src/safe_link.py")
    assert resolved.resolve() == target_file.resolve()
