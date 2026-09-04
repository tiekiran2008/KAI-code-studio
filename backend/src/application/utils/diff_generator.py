"""
Unified Diff Generator Utility
==============================
Deterministic, in-memory unified git diff generator for code fix suggestions.
Uses standard library difflib and does NOT perform shell/git execution or filesystem access.
"""
import difflib


def generate_unified_diff(
    original_code: str,
    proposed_code: str,
    file_path: str = "file.py",
    context_lines: int = 3,
) -> str:
    """
    Generates a unified git diff between original_code and proposed_code.

    Parameters:
    -----------
    original_code : str
        The original source code snippet.
    proposed_code : str
        The proposed/fixed source code snippet.
    file_path : str
        The relative file path used for diff header labels (default: "file.py").
    context_lines : int
        Number of context lines around changes (default: 3).

    Returns:
    --------
    str
        A formatted unified diff string (e.g. '--- a/path\n+++ b/path\n@@ ... @@\n...'),
        or an empty string if original_code and proposed_code are identical.
    """
    if original_code is None:
        original_code = ""
    if proposed_code is None:
        proposed_code = ""

    # Normalize CRLF to LF for deterministic line splitting
    norm_orig = original_code.replace("\r\n", "\n")
    norm_prop = proposed_code.replace("\r\n", "\n")

    # Identical code produces an empty diff
    if norm_orig == norm_prop:
        return ""

    # Split into line lists preserving line boundaries
    orig_lines = norm_orig.splitlines()
    prop_lines = norm_prop.splitlines()

    # Sanitize file_path for header display (prevent path escapes in labels)
    clean_path = (file_path or "file.py").strip().lstrip("/\\")
    from_label = f"a/{clean_path}"
    to_label = f"b/{clean_path}"

    diff_lines = list(
        difflib.unified_diff(
            orig_lines,
            prop_lines,
            fromfile=from_label,
            tofile=to_label,
            n=context_lines,
            lineterm="",
        )
    )

    if not diff_lines:
        return ""

    return "\n".join(diff_lines)
