"""
Unit Tests: Atomic File Patcher
===============================
Validates atomic snippet replacement, stale-source protection, ambiguous matches,
rollback on verification failure, newline handling, UTF-8 integrity, and concurrency behavior.
"""
import hashlib
import os
import pytest
from pathlib import Path

from src.application.services.atomic_patcher import AtomicFilePatcher
from src.domain.entities.patch import (
    PatchRequest,
    StaleSourceError,
    AmbiguousMatchError,
    TargetFileNotFoundError,
    EncodingError,
    PatchVerificationError,
)


@pytest.fixture
def patcher_workspace(tmp_path):
    """Fixture providing a temporary workspace with sample code files."""
    workspace = tmp_path / "repo"
    workspace.mkdir()

    # Simple python file
    math_py = workspace / "math.py"
    math_py.write_text(
        "def calculate(a, b):\n    # TODO: optimize\n    res = a + b\n    return res\n",
        encoding="utf-8",
    )

    # File with duplicate lines
    duplicate_py = workspace / "duplicate.py"
    duplicate_py.write_text(
        "x = 10\nprint(x)\nx = 10\nprint(x)\n",
        encoding="utf-8",
    )

    # CRLF file
    crlf_py = workspace / "crlf.py"
    crlf_py.write_bytes(
        b"def hello():\r\n    msg = 'hello'\r\n    return msg\r\n"
    )

    # UTF-8 with special characters / emojis
    unicode_py = workspace / "unicode.py"
    unicode_py.write_text(
        "# UTF-8 test: \u03c0 \u2248 3.14159 \u2764\u2728\ndef symbol():\n    return '\u03c0'\n",
        encoding="utf-8",
    )

    return {
        "root": workspace,
        "math_py": math_py,
        "duplicate_py": duplicate_py,
        "crlf_py": crlf_py,
        "unicode_py": unicode_py,
    }


def test_patch_exact_single_match_success(patcher_workspace):
    root = patcher_workspace["root"]
    math_file = patcher_workspace["math_py"]
    patcher = AtomicFilePatcher()

    req = PatchRequest(
        file_path="math.py",
        expected_original="    # TODO: optimize\n    res = a + b",
        proposed_replacement="    res = a * b",
    )

    result = patcher.apply_patch(root, req)

    assert result.success is True
    assert result.changed is True
    assert result.rollback_performed is False
    assert result.bytes_written > 0

    # Verify updated content on disk
    updated = math_file.read_text(encoding="utf-8")
    assert "    res = a * b\n    return res" in updated
    assert "TODO: optimize" not in updated


def test_patch_stale_source_no_match_rejected(patcher_workspace):
    root = patcher_workspace["root"]
    math_file = patcher_workspace["math_py"]
    original_content = math_file.read_text(encoding="utf-8")
    patcher = AtomicFilePatcher()

    req = PatchRequest(
        file_path="math.py",
        expected_original="def non_existent_function():\n    pass",
        proposed_replacement="def fixed():\n    pass",
    )

    with pytest.raises(StaleSourceError, match="Expected code snippet not found"):
        patcher.apply_patch(root, req)

    # Verify file remains completely untouched
    assert math_file.read_text(encoding="utf-8") == original_content


def test_patch_ambiguous_duplicate_match_rejected(patcher_workspace):
    root = patcher_workspace["root"]
    dup_file = patcher_workspace["duplicate_py"]
    original_content = dup_file.read_text(encoding="utf-8")
    patcher = AtomicFilePatcher()

    req = PatchRequest(
        file_path="duplicate.py",
        expected_original="x = 10",
        proposed_replacement="x = 20",
    )

    with pytest.raises(AmbiguousMatchError, match="occurs 2 times"):
        patcher.apply_patch(root, req)

    # Verify file remains untouched
    assert dup_file.read_text(encoding="utf-8") == original_content


def test_patch_identical_replacement_is_noop(patcher_workspace):
    root = patcher_workspace["root"]
    math_file = patcher_workspace["math_py"]
    original_content = math_file.read_text(encoding="utf-8")
    patcher = AtomicFilePatcher()

    snippet = "    res = a + b"
    req = PatchRequest(
        file_path="math.py",
        expected_original=snippet,
        proposed_replacement=snippet,
    )

    result = patcher.apply_patch(root, req)
    assert result.success is True
    assert result.changed is False
    assert result.bytes_written == 0
    assert math_file.read_text(encoding="utf-8") == original_content


def test_patch_crlf_newline_preservation(patcher_workspace):
    root = patcher_workspace["root"]
    crlf_file = patcher_workspace["crlf_py"]
    patcher = AtomicFilePatcher()

    req = PatchRequest(
        file_path="crlf.py",
        expected_original="    msg = 'hello'",
        proposed_replacement="    msg = 'world'",
    )

    result = patcher.apply_patch(root, req)
    assert result.success is True

    raw_bytes = crlf_file.read_bytes()
    assert b"\r\n" in raw_bytes
    assert b"msg = 'world'\r\n" in raw_bytes


def test_patch_unicode_special_chars_preserved(patcher_workspace):
    root = patcher_workspace["root"]
    unicode_file = patcher_workspace["unicode_py"]
    patcher = AtomicFilePatcher()

    req = PatchRequest(
        file_path="unicode.py",
        expected_original="def symbol():\n    return '\u03c0'",
        proposed_replacement="def symbol():\n    return '\u03c0 \u2764\u2728'",
    )

    result = patcher.apply_patch(root, req)
    assert result.success is True

    content = unicode_file.read_text(encoding="utf-8")
    assert "\u03c0 \u2764\u2728" in content


def test_patch_expected_hash_validation(patcher_workspace):
    root = patcher_workspace["root"]
    math_file = patcher_workspace["math_py"]
    current_hash = hashlib.sha256(math_file.read_bytes()).hexdigest()
    patcher = AtomicFilePatcher()

    # Mismatched hash -> StaleSourceError
    bad_req = PatchRequest(
        file_path="math.py",
        expected_original="    res = a + b",
        proposed_replacement="    res = a * b",
        expected_hash="0000000000000000000000000000000000000000000000000000000000000000",
    )
    with pytest.raises(StaleSourceError, match="File hash mismatch"):
        patcher.apply_patch(root, bad_req)

    # Correct hash -> Success
    good_req = PatchRequest(
        file_path="math.py",
        expected_original="    res = a + b",
        proposed_replacement="    res = a * b",
        expected_hash=current_hash,
    )
    result = patcher.apply_patch(root, good_req)
    assert result.success is True


def test_patch_missing_file_rejected(patcher_workspace):
    root = patcher_workspace["root"]
    patcher = AtomicFilePatcher()

    req = PatchRequest(
        file_path="missing.py",
        expected_original="x = 1",
        proposed_replacement="x = 2",
    )
    with pytest.raises(TargetFileNotFoundError, match="does not exist"):
        patcher.apply_patch(root, req)


def test_patch_non_utf8_file_rejected(patcher_workspace):
    root = patcher_workspace["root"]
    binary_file = root / "binary.dat"
    binary_file.write_bytes(b"\x80\x81\xff\xfe\x00\x01")
    patcher = AtomicFilePatcher()

    req = PatchRequest(
        file_path="binary.dat",
        expected_original="some text",
        proposed_replacement="new text",
    )
    with pytest.raises(EncodingError, match="not valid UTF-8"):
        patcher.apply_patch(root, req)


def test_patch_verification_failure_triggers_automatic_rollback(patcher_workspace, monkeypatch):
    root = patcher_workspace["root"]
    math_file = patcher_workspace["math_py"]
    original_bytes = math_file.read_bytes()
    patcher = AtomicFilePatcher()

    # Patch read_bytes on Path to simulate corrupt data during post-write verification read
    real_read_bytes = Path.read_bytes
    read_count = [0]

    def mock_read_bytes(self):
        read_count[0] += 1
        if read_count[0] == 2:  # Post-write verification read
            return b"corrupted post-write content"
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", mock_read_bytes)

    req = PatchRequest(
        file_path="math.py",
        expected_original="    res = a + b",
        proposed_replacement="    res = a * b",
    )

    with pytest.raises(PatchVerificationError, match="rolled back"):
        patcher.apply_patch(root, req)

    # Verify that rollback restored original content exactly byte-for-byte
    assert real_read_bytes(math_file) == original_bytes


def test_concurrency_race_second_patch_fails_as_stale(patcher_workspace):
    root = patcher_workspace["root"]
    math_file = patcher_workspace["math_py"]
    patcher = AtomicFilePatcher()

    # Two requests generated against the same original snippet
    req1 = PatchRequest(
        file_path="math.py",
        expected_original="    res = a + b",
        proposed_replacement="    res = a * b  # first apply",
    )
    req2 = PatchRequest(
        file_path="math.py",
        expected_original="    res = a + b",
        proposed_replacement="    res = a ** b  # second apply",
    )

    # First succeeds
    res1 = patcher.apply_patch(root, req1)
    assert res1.success is True

    # Second fails with StaleSourceError because the original snippet is gone
    with pytest.raises(StaleSourceError, match="Expected code snippet not found"):
        patcher.apply_patch(root, req2)
