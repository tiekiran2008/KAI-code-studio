import pytest
from src.application.rag.citation_validator import CitationValidator
from src.domain.models.rag import RerankedChunk, Citation


def test_citation_validator_evidence_pattern():
    validator = CitationValidator()

    chunks = [
        RerankedChunk(
            chunk_id="c1",
            repo_id="repo-1",
            file_path="src/processor.py",
            content="def analyze_performance():\n    pass",
            language="python",
            commit_hash="abc",
            symbol_name="analyze_performance",
            symbol_type="function",
            start_line=20,
            end_line=60,
            imports=[],
            embedding_score=0.9,
            symbol_importance_score=0.9,
            structure_score=0.9,
            file_relevance_score=0.9,
            dependency_score=0.9,
            metadata_score=0.9,
        )
    ]

    answer = (
        "### Weakness 1 — Inefficient performance loop\n"
        "Evidence: `src/processor.py#L29-57` — `analyze_performance()`\n\n"
        "Observed code:\nThe function processes items synchronously.\n\n"
        "Why it matters:\nLeads to high latency.\n\n"
        "Recommended improvement:\nUse batch processing.\n"
    )

    result = validator.validate_and_reconcile(answer, chunks)

    assert result.is_valid is True
    assert len(result.verified_citations) == 1
    assert result.verified_citations[0].file_path == "src/processor.py"
    assert result.verified_citations[0].start_line == 29
    assert result.verified_citations[0].end_line == 57
    assert result.grounding_score == 1.0


def test_citation_validator_unverified_file():
    validator = CitationValidator()

    chunks = [
        RerankedChunk(
            chunk_id="c1",
            repo_id="repo-1",
            file_path="src/real_file.py",
            content="class RealClass:\n    pass",
            language="python",
            commit_hash="abc",
            symbol_name="RealClass",
            symbol_type="class",
            start_line=1,
            end_line=20,
            imports=[],
            embedding_score=0.9,
            symbol_importance_score=0.9,
            structure_score=0.9,
            file_relevance_score=0.9,
            dependency_score=0.9,
            metadata_score=0.9,
        )
    ]

    answer = (
        "### Weakness 1 — Nonexistent issue\n"
        "Evidence: `src/fake_ghost_file.py#L10-20` — `fake_function()`\n"
    )

    result = validator.validate_and_reconcile(answer, chunks)

    assert result.is_valid is False
    assert len(result.unverified_citations) == 1
    assert result.unverified_citations[0]["file"] == "src/fake_ghost_file.py"
    assert result.grounding_score == 0.0


def test_citation_validator_tag_pattern():
    validator = CitationValidator()

    chunks = [
        RerankedChunk(
            chunk_id="c2",
            repo_id="repo-1",
            file_path="backend/src/main.py",
            content="app = FastAPI()",
            language="python",
            commit_hash="abc",
            symbol_name="app",
            symbol_type="variable",
            start_line=10,
            end_line=30,
            imports=[],
            embedding_score=0.85,
            symbol_importance_score=0.85,
            structure_score=0.85,
            file_relevance_score=0.85,
            dependency_score=0.85,
            metadata_score=0.85,
        )
    ]

    answer = "The app configuration is initialized in [FILE: main.py, LINES: 12-25, SYMBOL: app]."

    result = validator.validate_and_reconcile(answer, chunks)

    assert len(result.verified_citations) == 1
    assert "main.py" in result.verified_citations[0].file_path
    assert result.grounding_score == 1.0


def test_citation_validator_empty_answer():
    validator = CitationValidator()
    result = validator.validate_and_reconcile("", [])
    assert result.is_valid is True
    assert len(result.verified_citations) == 0
    assert result.grounding_score == 1.0
