"""
Path Sandbox Service
====================
Provides strict, write-safe path validation ensuring all file operations
remain strictly confined within an authorized repository workspace root.
"""
import os
import re
from pathlib import Path
from typing import Union

from src.domain.entities.patch import UnsafePathError, SymlinkEscapeError


class PathSandboxService:
    """Validates and resolves file paths against a trusted workspace root.

    Guards against:
    - Path traversal (../ and ..\\)
    - Absolute Unix and Windows paths
    - Drive-qualified Windows paths (C:, D:, etc.)
    - UNC network paths (\\\\server\\share)
    - Null byte injection (\\x00)
    - Symlink / reparse-point escapes pointing outside workspace
    - Root directory targets
    """

    @staticmethod
    def validate_path(
        workspace_root: Union[str, Path],
        relative_path: str,
        must_be_file: bool = False,
    ) -> Path:
        """Validate and resolve an untrusted relative path against workspace_root.

        Parameters
        ----------
        workspace_root : Union[str, Path]
            The trusted absolute root directory of the repository/workspace.
        relative_path : str
            The untrusted repository-relative file path.
        must_be_file : bool
            If True, ensures the resolved target is an existing regular file or does not exist as a directory.

        Returns
        -------
        Path
            The safe, fully resolved canonical Path object.

        Raises
        ------
        UnsafePathError
            If path format is invalid, absolute, traversal-prone, or escapes sandbox.
        SymlinkEscapeError
            If any symlink in the path chain points outside the workspace root.
        """
        # 1. Null byte check
        if "\x00" in str(relative_path):
            raise UnsafePathError("Null bytes are not allowed in file paths")

        clean_rel = str(relative_path).strip()
        if not clean_rel:
            raise UnsafePathError("File path cannot be empty or whitespace only")

        # 2. Reject UNC paths (\\host\share or //host/share)
        if clean_rel.startswith(("\\\\", "//")):
            raise UnsafePathError(f"UNC network paths are forbidden: '{clean_rel}'")

        # 3. Reject Windows drive-qualified paths (e.g. C:, D:)
        if re.match(r"^[a-zA-Z]:", clean_rel):
            raise UnsafePathError(f"Drive-qualified paths are forbidden: '{clean_rel}'")

        # 4. Reject absolute paths
        rel_obj = Path(clean_rel)
        if rel_obj.is_absolute() or clean_rel.startswith(("/", "\\")):
            raise UnsafePathError(f"Absolute paths are forbidden: '{clean_rel}'")

        # 5. Reject explicit traversal segments (.. or /../ or \\..\\)
        parts = rel_obj.parts
        if ".." in parts:
            raise UnsafePathError(f"Directory traversal '..' is forbidden: '{clean_rel}'")

        # 6. Canonicalize workspace_root
        root_path = Path(workspace_root).resolve()
        if not root_path.exists():
            raise UnsafePathError(f"Workspace root does not exist: '{workspace_root}'")
        if not root_path.is_dir():
            raise UnsafePathError(f"Workspace root must be a directory: '{workspace_root}'")

        # 7. Construct candidate target and resolve
        candidate = root_path / rel_obj
        try:
            resolved_target = candidate.resolve()
        except Exception as exc:
            raise UnsafePathError(f"Could not resolve path '{clean_rel}': {exc}")

        # 8. Boundary check: must be strictly inside root_path
        try:
            resolved_target.relative_to(root_path)
        except ValueError:
            raise UnsafePathError(
                f"Path traversal detected: '{clean_rel}' escapes workspace boundary"
            )

        # 9. Target cannot be the root directory itself
        if resolved_target == root_path:
            raise UnsafePathError("Target path cannot be the workspace root directory itself")

        # 10. Symlink inspection: check for any symlinks in the path hierarchy
        # Traverse from root down to candidate to detect symlinks that escape sandbox
        current = root_path
        for part in rel_obj.parts:
            current = current / part
            if current.is_symlink():
                try:
                    symlink_target = current.resolve()
                    symlink_target.relative_to(root_path)
                except ValueError:
                    raise SymlinkEscapeError(
                        f"Symlink '{current.name}' points outside workspace boundary"
                    )

        # 11. Optional file check
        if must_be_file and resolved_target.is_dir():
            raise UnsafePathError(f"Target path is a directory, not a file: '{clean_rel}'")

        return resolved_target
