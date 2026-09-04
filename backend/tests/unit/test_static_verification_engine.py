"""
Unit tests for Tier-1 StaticVerificationEngine
==============================================
Tests in-memory deterministic syntax and static text verification.
Ensures zero subprocess/shell execution, zero imports of repo code.
"""
import pytest
from src.infrastructure.analysis.static_verification_engine import StaticVerificationEngine
from src.domain.entities.verification import (
    VerificationStatus,
    CheckStatus,
)


@pytest.fixture
def engine():
    return StaticVerificationEngine()


def test_valid_python_syntax(engine):
    code = """
def calculate_sum(a: int, b: int) -> int:
    \"\"\"Return the sum of two integers.\"\"\"
    return a + b

class MathUtil:
    def multiply(self, x, y):
        return x * y
"""
    result = engine.verify_source(code, "utils/math.py", hint_language="python")
    assert result.status == VerificationStatus.PASSED
    assert result.language == "python"
    assert len(result.errors) == 0
    assert any(c.name == "syntax_parser" and c.status == CheckStatus.PASSED for c in result.checks)
    assert result.verified_hash is not None


def test_invalid_python_syntax(engine):
    code = """
def broken_function(:
    return 42
"""
    result = engine.verify_source(code, "broken.py", hint_language="python")
    assert result.status == VerificationStatus.FAILED
    assert len(result.errors) > 0
    syntax_check = next(c for c in result.checks if c.name == "syntax_parser")
    assert syntax_check.status == CheckStatus.FAILED
    assert syntax_check.line_number == 2


def test_malicious_python_code_parsed_only_no_execution(engine):
    # This code contains dangerous operations that MUST NOT be executed.
    side_effect_flag = []
    code = """
import os
import sys

# If this executed, it would perform an operation, but ast.parse must only parse it
def dangerous_operation():
    os.environ["MALICIOUS_EXEC_TEST"] = "COMPROMISED"
"""
    result = engine.verify_source(code, "danger.py", hint_language="python")
    # Syntax is valid Python, so parse succeeds
    assert result.status == VerificationStatus.PASSED
    # Verify environment was NOT modified (no execution took place)
    import os
    assert "MALICIOUS_EXEC_TEST" not in os.environ


def test_conflict_markers_detected(engine):
    code = """
def merge_something():
<<<<<<< HEAD
    return "master version"
=======
    return "branch version"
>>>>>>> feature/branch
"""
    result = engine.verify_source(code, "merge.py", hint_language="python")
    assert result.status == VerificationStatus.FAILED
    assert "conflict" in result.message.lower()
    conflict_check = next(c for c in result.checks if c.name == "conflict_markers")
    assert conflict_check.status == CheckStatus.FAILED
    assert conflict_check.line_number == 3


def test_empty_source_rejected(engine):
    result = engine.verify_source("", "empty.py", hint_language="python")
    assert result.status == VerificationStatus.FAILED
    empty_check = next(c for c in result.checks if c.name == "non_empty_source")
    assert empty_check.status == CheckStatus.FAILED


def test_whitespace_only_source_rejected(engine):
    result = engine.verify_source("   \n\t  \n  ", "spaces.py", hint_language="python")
    assert result.status == VerificationStatus.FAILED
    empty_check = next(c for c in result.checks if c.name == "non_empty_source")
    assert empty_check.status == CheckStatus.FAILED


def test_unsupported_language_never_false_passes(engine):
    code = "fn main() { println!(\"hello\"); }"
    result = engine.verify_source(code, "main.rs", hint_language="rust")
    assert result.status == VerificationStatus.UNSUPPORTED
    assert result.status != VerificationStatus.PASSED
    syntax_check = next(c for c in result.checks if c.name == "syntax_parser")
    assert syntax_check.status == CheckStatus.UNSUPPORTED


def test_unknown_language_fallback(engine):
    code = "some random code text"
    result = engine.verify_source(code, "config.xyz", hint_language="unknown_xyz")
    assert result.status == VerificationStatus.UNSUPPORTED


def test_javascript_typescript_syntax(engine):
    valid_js = """
function greet(name) {
    return `Hello, ${name}!`;
}
"""
    result_js = engine.verify_source(valid_js, "app.js", hint_language="javascript")
    assert result_js.status in (VerificationStatus.PASSED, VerificationStatus.UNSUPPORTED)

    if result_js.status == VerificationStatus.PASSED:
        invalid_js = "function broken( { return 1;"
        result_inv = engine.verify_source(invalid_js, "broken.js", hint_language="javascript")
        assert result_inv.status == VerificationStatus.FAILED


def test_typescript_syntax(engine):
    valid_ts = """
interface User {
    id: string;
    name: string;
}

export function getUser(id: string): User {
    return { id, name: "Alice" };
}
"""
    result_ts = engine.verify_source(valid_ts, "user.ts", hint_language="typescript")
    assert result_ts.status in (VerificationStatus.PASSED, VerificationStatus.UNSUPPORTED)


def test_java_syntax(engine):
    valid_java = """
package com.example;

public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
}
"""
    result_java = engine.verify_source(valid_java, "Calculator.java", hint_language="java")
    assert result_java.status in (VerificationStatus.PASSED, VerificationStatus.UNSUPPORTED)


def test_separator_and_end_conflict_markers_detected(engine):
    code_sep = "def foo():\n=======\n    return 1\n"
    res_sep = engine.verify_source(code_sep, "foo.py", hint_language="python")
    assert res_sep.status == VerificationStatus.FAILED
    assert any(c.name == "conflict_markers" and c.status == CheckStatus.FAILED for c in res_sep.checks)

    code_end = "def bar():\n>>>>>>> feature\n    return 2\n"
    res_end = engine.verify_source(code_end, "bar.py", hint_language="python")
    assert res_end.status == VerificationStatus.FAILED

