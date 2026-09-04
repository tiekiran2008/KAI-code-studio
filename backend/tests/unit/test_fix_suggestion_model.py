"""
test_fix_suggestion_model.py
=============================
Unit tests for FixSuggestion domain entity and ReviewFinding integration.
"""
import pytest
from pydantic import ValidationError

from src.domain.entities.fix_suggestion import (
    FixSuggestion,
    FixValidationStatus,
    FixUserDecision,
)
from src.domain.entities.code_review import ReviewFinding, SeverityEnum


def test_1_valid_fix_suggestion_creation():
    """Valid FixSuggestion model instantiation."""
    fix = FixSuggestion(
        finding_index=0,
        file_path="src/main.py",
        original_code="def foo(): pass",
        proposed_code="def foo(): return 42",
        explanation="Return valid result",
        diff="--- a/src/main.py\n+++ b/src/main.py\n-def foo(): pass\n+def foo(): return 42",
        confidence_score=0.95,
        validation_status=FixValidationStatus.VALID,
        user_decision=FixUserDecision.PENDING,
        language="python",
        validation_message="Syntax valid",
    )
    assert fix.finding_index == 0
    assert fix.file_path == "src/main.py"
    assert fix.confidence_score == 0.95
    assert fix.validation_status == FixValidationStatus.VALID
    assert fix.user_decision == FixUserDecision.PENDING


def test_2_finding_index_negative_fails():
    """finding_index < 0 raises ValidationError."""
    with pytest.raises(ValidationError):
        FixSuggestion(
            finding_index=-1,
            file_path="src/main.py",
            original_code="a = 1",
            proposed_code="a = 2",
            explanation="Fix value",
        )


def test_3_confidence_score_below_zero_fails():
    """confidence_score < 0.0 raises ValidationError."""
    with pytest.raises(ValidationError):
        FixSuggestion(
            finding_index=0,
            file_path="src/main.py",
            original_code="a = 1",
            proposed_code="a = 2",
            explanation="Fix value",
            confidence_score=-0.1,
        )


def test_4_confidence_score_above_one_fails():
    """confidence_score > 1.0 raises ValidationError."""
    with pytest.raises(ValidationError):
        FixSuggestion(
            finding_index=0,
            file_path="src/main.py",
            original_code="a = 1",
            proposed_code="a = 2",
            explanation="Fix value",
            confidence_score=1.5,
        )


def test_5_empty_original_code_fails():
    """empty or whitespace original_code raises ValidationError."""
    with pytest.raises(ValidationError):
        FixSuggestion(
            finding_index=0,
            file_path="src/main.py",
            original_code="   ",
            proposed_code="a = 2",
            explanation="Fix value",
        )


def test_6_empty_proposed_code_fails():
    """empty or whitespace proposed_code raises ValidationError."""
    with pytest.raises(ValidationError):
        FixSuggestion(
            finding_index=0,
            file_path="src/main.py",
            original_code="a = 1",
            proposed_code="",
            explanation="Fix value",
        )


def test_7_empty_file_path_or_explanation_fails():
    """empty file_path or explanation raises ValidationError."""
    with pytest.raises(ValidationError):
        FixSuggestion(
            finding_index=0,
            file_path="",
            original_code="a = 1",
            proposed_code="a = 2",
            explanation="Fix value",
        )
    with pytest.raises(ValidationError):
        FixSuggestion(
            finding_index=0,
            file_path="main.py",
            original_code="a = 1",
            proposed_code="a = 2",
            explanation="   ",
        )


def test_8_serialization_round_trip():
    """FixSuggestion model_dump() -> dict -> FixSuggestion round-trip."""
    original_fix = FixSuggestion(
        finding_index=2,
        file_path="backend/src/utils.py",
        original_code="x = 10",
        proposed_code="x = 20",
        explanation="Update constant",
        diff="--- a/backend/src/utils.py\n+++ b/backend/src/utils.py\n-x = 10\n+x = 20",
        confidence_score=0.9,
    )
    raw_dict = original_fix.model_dump()
    assert isinstance(raw_dict, dict)
    assert raw_dict["finding_index"] == 2
    assert raw_dict["validation_status"] == "pending"
    assert raw_dict["user_decision"] == "pending"

    reconstructed = FixSuggestion(**raw_dict)
    assert reconstructed == original_fix


def test_9_existing_review_finding_without_fix_suggestion():
    """Existing ReviewFinding without fix_suggestion deserializes cleanly."""
    finding_data = {
        "issue": "SQL Injection risk",
        "severity": "high",
        "explanation": "Unsanitized user input in raw SQL query.",
        "suggested_fix": "Use parameterized queries.",
        "confidence_score": 0.98,
        "file_path": "db/query.py",
        "line_number": 45,
    }
    finding = ReviewFinding(**finding_data)
    assert finding.issue == "SQL Injection risk"
    assert finding.fix_suggestion is None


def test_10_review_finding_with_fix_suggestion_integration():
    """ReviewFinding with embedded FixSuggestion serializes and deserializes correctly."""
    fix = FixSuggestion(
        finding_index=0,
        file_path="db/query.py",
        original_code='db.execute(f"SELECT * FROM users WHERE id = {user_id}")',
        proposed_code='db.execute("SELECT * FROM users WHERE id = :id", {"id": user_id})',
        explanation="Parameterized SQL query prevents injection.",
        diff="--- a/db/query.py\n+++ b/db/query.py\n...",
        confidence_score=0.98,
        validation_status=FixValidationStatus.VALID,
    )

    finding = ReviewFinding(
        issue="SQL Injection risk",
        severity=SeverityEnum.HIGH,
        explanation="Unsanitized user input in raw SQL query.",
        suggested_fix="Use parameterized queries.",
        confidence_score=0.98,
        file_path="db/query.py",
        line_number=45,
        fix_suggestion=fix,
    )

    raw_dict = finding.model_dump()
    assert raw_dict["fix_suggestion"]["finding_index"] == 0
    assert raw_dict["fix_suggestion"]["validation_status"] == "valid"

    reconstructed = ReviewFinding(**raw_dict)
    assert reconstructed.fix_suggestion is not None
    assert reconstructed.fix_suggestion.file_path == "db/query.py"
    assert reconstructed.fix_suggestion.validation_status == FixValidationStatus.VALID
