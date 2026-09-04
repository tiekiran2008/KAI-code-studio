"""
Ephemeral Workspace Manager
===========================
Creates and manages isolated copy-on-execution repository workspaces with path safety
and credential file filtering, guaranteeing that original repositories are never mutated.
"""
from fnmatch import fnmatch
import os
from pathlib import Path
import shutil
import tempfile
from typing import Set

from src.core.logger import logger
from src.core.errors import WorkflowExecutionError
from src.infrastructure.filesystem.path_sandbox import PathSandboxService

# Sensitive directory patterns excluded from ephemeral sandbox copies
EXCLUDED_DIR_PATTERNS: Set[str] = {
    ".git",
    ".svn",
    ".hg",
    ".venv",
    "venv",
    "env",
    ".env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".idea",
    ".vscode",
}

# Sensitive credential and secret file patterns excluded from ephemeral copies
EXCLUDED_FILE_PATTERNS: Set[str] = {
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.id_rsa",
    "*.id_dsa",
    "*.id_ecdsa",
    "*.id_ed25519",
    "*.pfx",
    "*.p12",
    "*.kdbx",
    "*.jks",
    "*.pyc",
    "*.pyo",
    "*.pyd",
}

MAX_COPY_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_TOTAL_WORKSPACE_SIZE_BYTES = 200 * 1024 * 1024  # 200 MB


class EphemeralWorkspaceContext:
    """Active ephemeral workspace context supporting explicit and context-manager cleanup."""

    def __init__(self, source_path: Path, temp_path: Path) -> None:
        self.source_path = source_path
        self.temp_path = temp_path
        self.is_cleaned = False

    def cleanup(self) -> None:
        """Purge temporary directory and all contents."""
        if not self.is_cleaned and self.temp_path.exists():
            try:
                shutil.rmtree(self.temp_path, ignore_errors=True)
                self.is_cleaned = True
                logger.debug(f"Ephemeral workspace cleaned: {self.temp_path}")
            except Exception as exc:
                logger.warning(f"Error cleaning ephemeral workspace {self.temp_path}: {exc}")

    async def __aenter__(self) -> "EphemeralWorkspaceContext":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()


class EphemeralWorkspaceManager:
    """Manages the creation and cleanup of isolated copy-on-execution temporary workspaces."""

    def __init__(self, path_sandbox: PathSandboxService = None) -> None:
        self.sandbox = path_sandbox or PathSandboxService()

    @staticmethod
    def _is_excluded_file(filename: str) -> bool:
        """Check if a file matches any excluded/sensitive credential pattern."""
        for pattern in EXCLUDED_FILE_PATTERNS:
            if fnmatch(filename, pattern):
                return True
        return False

    @staticmethod
    def _is_excluded_dir(dirname: str) -> bool:
        """Check if a directory matches any excluded directory pattern."""
        return dirname in EXCLUDED_DIR_PATTERNS

    def create_snapshot(self, source_workspace_root: str) -> EphemeralWorkspaceContext:
        """Create a sanitized, isolated temporary copy of the repository workspace.

        Parameters
        ----------
        source_workspace_root : str
            Absolute path to the source repository on the host.

        Returns
        -------
        EphemeralWorkspaceContext
            Context containing the safe temporary directory and cleanup handler.

        Raises
        ------
        WorkflowExecutionError
            If source does not exist, exceeds size bounds, or contains path escapes.
        """
        source_path = Path(source_workspace_root).resolve()
        if not source_path.exists() or not source_path.is_dir():
            raise WorkflowExecutionError(
                f"Source workspace root does not exist or is not a directory: '{source_workspace_root}'"
            )

        # Create temporary root
        temp_dir = Path(tempfile.mkdtemp(prefix="agent_sandbox_ws_")).resolve()
        total_copied_bytes = 0

        try:
            for root, dirs, files in os.walk(source_path, topdown=True, followlinks=False):
                # Filter out excluded directories in-place
                dirs[:] = [d for d in dirs if not self._is_excluded_dir(d)]

                current_root = Path(root)
                rel_root = current_root.relative_to(source_path)
                dest_dir = temp_dir / rel_root
                dest_dir.mkdir(parents=True, exist_ok=True)

                for file_name in files:
                    if self._is_excluded_file(file_name):
                        continue

                    src_file = current_root / file_name

                    # Resolve symlinks and ensure they do not escape source_path
                    if src_file.is_symlink():
                        try:
                            resolved_link = src_file.resolve()
                            resolved_link.relative_to(source_path)
                        except (ValueError, RuntimeError):
                            logger.warning(f"Skipping symlink escaping workspace root: {src_file}")
                            continue

                    try:
                        file_stat = src_file.stat()
                        file_size = file_stat.st_size
                    except (OSError, PermissionError):
                        continue

                    if file_size > MAX_COPY_FILE_SIZE_BYTES:
                        logger.warning(f"Skipping oversized file ({file_size} bytes): {src_file}")
                        continue

                    total_copied_bytes += file_size
                    if total_copied_bytes > MAX_TOTAL_WORKSPACE_SIZE_BYTES:
                        raise WorkflowExecutionError(
                            f"Workspace exceeds maximum copy limit of {MAX_TOTAL_WORKSPACE_SIZE_BYTES} bytes"
                        )

                    dest_file = dest_dir / file_name
                    shutil.copy2(src_file, dest_file)

            return EphemeralWorkspaceContext(source_path=source_path, temp_path=temp_dir)

        except Exception as exc:
            # On creation failure, immediately purge temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            if isinstance(exc, WorkflowExecutionError):
                raise
            raise WorkflowExecutionError(f"Failed to create ephemeral workspace snapshot: {exc}")
