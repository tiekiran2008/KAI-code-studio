"""
Pytest Sandbox Runner
=====================
Command allowlisting, output bounding (64KB), and deterministic test result parsing
specifically for Python pytest workloads.
"""
import re
from typing import List, Optional, Tuple

from src.core.errors import WorkflowExecutionError

# Fixed immutable base argv template for pytest in sandbox
BASE_PYTEST_ARGV: List[str] = [
    "pytest",
    "-q",
    "--tb=short",
    "--no-header",
    "--capture=sys",
    "--maxfail=10",
]

# Prohibited shell metacharacters in target paths
FORBIDDEN_PATH_CHARS = set(";&|><$`\"'\\{}()!\n\r\t")

# Output bounding threshold
MAX_OUTPUT_CHARS = 64 * 1024  # 64 KB


class PytestSandboxRunner:
    """Manages trusted command generation, output bounding, and result parsing for pytest."""

    @staticmethod
    def build_command(relative_target_path: Optional[str] = None) -> List[str]:
        """Generate trusted command argv array for pytest execution.

        Parameters
        ----------
        relative_target_path : Optional[str]
            Optional relative path to a specific test file or test directory.

        Returns
        -------
        List[str]
            Immutable argv list for container execution.

        Raises
        ------
        WorkflowExecutionError
            If target path contains prohibited flags, traversal, or shell metacharacters.
        """
        cmd = list(BASE_PYTEST_ARGV)
        if not relative_target_path:
            return cmd

        clean_path = str(relative_target_path).strip()
        if not clean_path:
            return cmd

        # Reject any argument starting with a flag indicator
        if clean_path.startswith("-"):
            raise WorkflowExecutionError(f"Target path cannot be a command-line flag: '{clean_path}'")

        # Reject prohibited shell metacharacters
        if any(ch in FORBIDDEN_PATH_CHARS for ch in clean_path):
            raise WorkflowExecutionError(f"Target path contains illegal metacharacters: '{clean_path}'")

        # Reject directory traversal
        if ".." in clean_path.split("/") or ".." in clean_path.split("\\"):
            raise WorkflowExecutionError(f"Directory traversal forbidden in target path: '{clean_path}'")

        cmd.append(clean_path)
        return cmd

    @staticmethod
    def bound_output(text: Optional[str]) -> str:
        """Truncate output at 64 KB with a clear truncation indicator."""
        if not text:
            return ""
        if len(text) <= MAX_OUTPUT_CHARS:
            return text
        return text[:MAX_OUTPUT_CHARS] + "\n[OUTPUT TRUNCATED: Exceeded 64KB limit]"

    @staticmethod
    def parse_pytest_summary(stdout: str) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
        """Extract total, passed, failed, and skipped test counts from pytest output.

        Returns
        -------
        Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]
            (total, passed, failed, skipped)
        """
        passed: Optional[int] = None
        failed: Optional[int] = None
        skipped: Optional[int] = None

        # Matches patterns like:
        # "5 passed, 1 failed, 2 skipped in 0.12s"
        # "3 passed in 0.05s"
        # "1 failed in 0.02s"
        passed_match = re.search(r"(\d+)\s+passed", stdout)
        if passed_match:
            passed = int(passed_match.group(1))

        failed_match = re.search(r"(\d+)\s+failed", stdout)
        if failed_match:
            failed = int(failed_match.group(1))

        skipped_match = re.search(r"(\d+)\s+skipped", stdout)
        if skipped_match:
            skipped = int(skipped_match.group(1))

        if passed is not None or failed is not None or skipped is not None:
            total = (passed or 0) + (failed or 0) + (skipped or 0)
            return total, passed or 0, failed or 0, skipped or 0

        return None, None, None, None
