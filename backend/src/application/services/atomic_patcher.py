"""
Atomic File Patcher Service
===========================
Executes deterministic, in-memory, exact-match code replacements with:
- Strict path sandboxing
- Stale-source detection
- Ambiguous match rejection
- Atomic temporary-file replacement
- Post-write verification and automatic rollback
- Safe logging (no source code leakage)

CRITICAL: This service does NOT execute code, shell commands, or git commands.
"""
import hashlib
import os
import uuid
from pathlib import Path
from typing import Optional, Union

from src.core.logger import logger
from src.domain.entities.patch import (
    PatchRequest,
    PatchResult,
    PatchError,
    TargetFileNotFoundError,
    StaleSourceError,
    AmbiguousMatchError,
    EncodingError,
    AtomicWriteError,
    PatchVerificationError,
    RollbackError,
)
from src.infrastructure.filesystem.path_sandbox import PathSandboxService


class AtomicFilePatcher:
    """Deterministic, atomic file patching engine."""

    def __init__(self, sandbox_service: Optional[PathSandboxService] = None) -> None:
        self.sandbox = sandbox_service or PathSandboxService()

    def apply_patch(
        self,
        workspace_root: Union[str, Path],
        request: PatchRequest,
    ) -> PatchResult:
        """Apply a patch request atomically to a file inside workspace_root.

        Parameters
        ----------
        workspace_root : Union[str, Path]
            The trusted workspace root directory.
        request : PatchRequest
            The patch request specifying file path, expected original, and proposed replacement.

        Returns
        -------
        PatchResult
            Metadata regarding the patch execution.

        Raises
        ------
        UnsafePathError / SymlinkEscapeError
            If file path violates sandbox constraints.
        TargetFileNotFoundError
            If target file does not exist on disk.
        StaleSourceError
            If expected snippet or file hash does not match current file.
        AmbiguousMatchError
            If expected snippet occurs more than once in the target file.
        EncodingError
            If file content cannot be read or decoded as UTF-8.
        AtomicWriteError
            If temporary write or atomic replace fails.
        PatchVerificationError
            If post-write verification fails (triggers rollback).
        """
        # 1. Validate sandboxed target path
        target_path = self.sandbox.validate_path(
            workspace_root=workspace_root,
            relative_path=request.file_path,
            must_be_file=True,
        )

        if not target_path.exists() or not target_path.is_file():
            raise TargetFileNotFoundError(f"Target file does not exist: '{request.file_path}'")

        # 2. Read original file
        try:
            original_bytes = target_path.read_bytes()
        except Exception as exc:
            raise TargetFileNotFoundError(f"Failed to read target file '{request.file_path}': {exc}")

        try:
            current_content = original_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EncodingError(f"Target file '{request.file_path}' is not valid UTF-8: {exc}")

        # 3. Compute baseline hash
        previous_hash = hashlib.sha256(original_bytes).hexdigest()

        # Optional pre-condition hash check
        if request.expected_hash and request.expected_hash.strip():
            if request.expected_hash.strip().lower() != previous_hash.lower():
                raise StaleSourceError(
                    f"File hash mismatch for '{request.file_path}': expected {request.expected_hash}, current is {previous_hash}"
                )

        # 4. Check if replacement is identical (no-op)
        if request.expected_original == request.proposed_replacement:
            logger.info(
                "patch_noop_identical_content",
                file_path=request.file_path,
                hash=previous_hash,
            )
            return PatchResult(
                file_path=request.file_path,
                success=True,
                changed=False,
                previous_hash=previous_hash,
                new_hash=previous_hash,
                bytes_written=0,
                rollback_performed=False,
                message="No changes needed: replacement is identical to original snippet",
            )

        # 5. Handle newline conventions
        # Detect if file uses CRLF vs LF
        has_crlf = "\r\n" in current_content
        expected_orig = request.expected_original
        proposed_repl = request.proposed_replacement

        if has_crlf:
            # Normalize snippet newlines to match file's CRLF
            expected_orig = expected_orig.replace("\r\n", "\n").replace("\n", "\r\n")
            proposed_repl = proposed_repl.replace("\r\n", "\n").replace("\n", "\r\n")
        else:
            # Normalize snippet newlines to LF
            expected_orig = expected_orig.replace("\r\n", "\n")
            proposed_repl = proposed_repl.replace("\r\n", "\n")

        # 6. Exact snippet search & uniqueness validation
        match_count = current_content.count(expected_orig)

        if match_count == 0:
            # Fallback: check if raw expected_original matches without newline normalization
            if current_content.count(request.expected_original) == 1:
                expected_orig = request.expected_original
                proposed_repl = request.proposed_replacement
                match_count = 1

        if match_count == 0:
            raise StaleSourceError(
                f"Expected code snippet not found in '{request.file_path}' (source may have been modified or is stale)"
            )

        if match_count > 1:
            raise AmbiguousMatchError(
                f"Expected code snippet occurs {match_count} times in '{request.file_path}'; cannot uniquely patch"
            )

        # 7. Perform in-memory replacement
        new_content = current_content.replace(expected_orig, proposed_repl, 1)
        new_bytes = new_content.encode("utf-8")
        new_hash = hashlib.sha256(new_bytes).hexdigest()

        # 8. Atomic file write via sibling temp file
        temp_file = target_path.with_name(f".{target_path.name}.{uuid.uuid4().hex}.tmp")

        try:
            with open(temp_file, "wb") as f:
                f.write(new_bytes)
                f.flush()
                os.fsync(f.fileno())
        except Exception as exc:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            raise AtomicWriteError(f"Failed writing temporary patch file: {exc}")

        # 9. Atomic replacement
        try:
            os.replace(temp_file, target_path)
        except Exception as exc:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            raise AtomicWriteError(f"Atomic replacement failed for '{request.file_path}': {exc}")

        # 10. Post-write verification
        verification_passed = False
        try:
            re_read_bytes = target_path.read_bytes()
            if hashlib.sha256(re_read_bytes).hexdigest() == new_hash:
                verification_passed = True
        except Exception as exc:
            logger.error("patch_verification_read_failed", file_path=request.file_path, error=str(exc))

        if not verification_passed:
            # Perform automatic rollback
            rollback_success = False
            rollback_temp = target_path.with_name(f".{target_path.name}.rollback.{uuid.uuid4().hex}.tmp")
            try:
                with open(rollback_temp, "wb") as f:
                    f.write(original_bytes)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(rollback_temp, target_path)
                rollback_success = True
            except Exception as rb_exc:
                logger.critical("patch_rollback_failed", file_path=request.file_path, error=str(rb_exc))
                if rollback_temp.exists():
                    try:
                        rollback_temp.unlink()
                    except Exception:
                        pass
                raise RollbackError(f"Verification failed AND rollback failed for '{request.file_path}': {rb_exc}")

            if rollback_success:
                raise PatchVerificationError(
                    f"Post-write verification failed for '{request.file_path}'; original content was rolled back"
                )

        logger.info(
            "patch_applied_successfully",
            file_path=request.file_path,
            bytes_written=len(new_bytes),
            previous_hash=previous_hash[:8],
            new_hash=new_hash[:8],
        )

        return PatchResult(
            file_path=request.file_path,
            success=True,
            changed=True,
            previous_hash=previous_hash,
            new_hash=new_hash,
            bytes_written=len(new_bytes),
            rollback_performed=False,
            message="Patch applied atomically and verified successfully",
        )
