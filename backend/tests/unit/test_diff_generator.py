"""
test_diff_generator.py
======================
Unit tests for deterministic in-memory unified diff generator utility.
"""
import pytest
from src.application.utils.diff_generator import generate_unified_diff


def test_1_single_line_replacement():
    """Single line code replacement produces valid unified diff."""
    original = "x = 1"
    proposed = "x = 2"
    path = "src/config.py"

    diff = generate_unified_diff(original, proposed, file_path=path)

    assert "--- a/src/config.py" in diff
    assert "+++ b/src/config.py" in diff
    assert "-x = 1" in diff
    assert "+x = 2" in diff


def test_2_multiline_replacement():
    """Multiline replacement produces correct unified diff hunks."""
    original = "def calculate(a, b):\n    return a + b"
    proposed = "def calculate(a: int, b: int) -> int:\n    \"\"\"Sum two numbers.\"\"\"\n    return a + b"
    path = "src/math_utils.py"

    diff = generate_unified_diff(original, proposed, file_path=path)

    assert "--- a/src/math_utils.py" in diff
    assert "+++ b/src/math_utils.py" in diff
    assert "-def calculate(a, b):" in diff
    assert "+def calculate(a: int, b: int) -> int:" in diff
    assert '+\n    """Sum two numbers."""' in diff or '+    """Sum two numbers."""' in diff


def test_3_line_insertion():
    """Inserted lines produce '+' lines without deleting original code."""
    original = "import os\n\ndef main():\n    pass"
    proposed = "import os\nimport sys\n\ndef main():\n    pass"
    path = "app.py"

    diff = generate_unified_diff(original, proposed, file_path=path)

    assert "--- a/app.py" in diff
    assert "+++ b/app.py" in diff
    assert "+import sys" in diff


def test_4_line_deletion():
    """Deleted lines produce '-' lines."""
    original = "import os\nimport unused_lib\n\ndef run():\n    os.getcwd()"
    proposed = "import os\n\ndef run():\n    os.getcwd()"
    path = "run.py"

    diff = generate_unified_diff(original, proposed, file_path=path)

    assert "--- a/run.py" in diff
    assert "+++ b/run.py" in diff
    assert "-import unused_lib" in diff


def test_5_identical_code_returns_empty_diff():
    """Identical original and proposed code returns empty string diff."""
    code = "def foo():\n    return True\n"
    diff = generate_unified_diff(code, code, file_path="same.py")
    assert diff == ""


def test_6_no_trailing_newline():
    """Code snippets without trailing newline are handled cleanly."""
    original = "print('hello')"
    proposed = "print('hello world')"
    diff = generate_unified_diff(original, proposed, file_path="hello.py")

    assert "--- a/hello.py" in diff
    assert "+++ b/hello.py" in diff
    assert "-print('hello')" in diff
    assert "+print('hello world')" in diff


def test_7_crlf_normalization():
    """Windows CRLF input is normalized so diff comparison is clean."""
    original = "line1\r\nline2\r\n"
    proposed = "line1\r\nline2_modified\r\n"
    diff = generate_unified_diff(original, proposed, file_path="crlf.py")

    assert "-line2" in diff
    assert "+line2_modified" in diff
    assert "\r" not in diff  # Normalized to LF


def test_8_file_label_sanitization():
    """File path stripping and header formatting work correctly."""
    diff = generate_unified_diff("a = 1", "a = 2", file_path="/root/project/test.py")
    assert "--- a/root/project/test.py" in diff
    assert "+++ b/root/project/test.py" in diff
