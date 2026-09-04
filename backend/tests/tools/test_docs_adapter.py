"""
Unit Tests — Documentation Search Tool Adapter
===============================================
Tests DocumentationSearchAdapter initialization with real/mocked QueryProcessor
and execution of documentation search queries.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.infrastructure.tools.adapters.docs import DocumentationSearchAdapter
from src.domain.models.tools import PermissionLevel


@pytest.fixture
def mock_query_processor():
    processor = MagicMock()
    processor.process_query = AsyncMock(return_value={
        "answer": "FastAPI is a modern, fast web framework for building APIs with Python.",
        "citations": [{"file_path": "docs/main.md", "start_line": 1, "end_line": 10}],
    })
    return processor


@pytest.fixture
def docs_adapter(mock_query_processor):
    return DocumentationSearchAdapter(query_processor=mock_query_processor)


def test_docs_adapter_metadata(docs_adapter):
    metadata = docs_adapter.get_metadata()
    assert metadata.name == "docs_search"
    assert metadata.permissions == PermissionLevel.READ_ONLY
    assert "query" in metadata.input_schema["properties"]
    assert "repo_id" in metadata.input_schema["properties"]
    assert "doc_type" in metadata.input_schema["properties"]


@pytest.mark.asyncio
async def test_docs_adapter_execute_success(docs_adapter, mock_query_processor):
    result = await docs_adapter.execute(
        query="Explain API routing",
        doc_type="indexed",
        repo_id="repo-123",
    )

    assert result.success is True
    assert "FastAPI" in result.data["answer"]
    assert len(result.data["citations"]) == 1
    mock_query_processor.process_query.assert_awaited_once_with(
        "Explain API routing",
        repo_id="repo-123",
        session_id=None,
    )


@pytest.mark.asyncio
async def test_docs_adapter_missing_required_parameters(docs_adapter):
    result_missing_query = await docs_adapter.execute(
        query="",
        doc_type="indexed",
        repo_id="repo-123",
    )
    assert result_missing_query.success is False
    assert "Missing query" in result_missing_query.error

    result_missing_repo = await docs_adapter.execute(
        query="What is this?",
        doc_type="indexed",
        repo_id="",
    )
    assert result_missing_repo.success is False
    assert "repo_id" in result_missing_repo.error


@pytest.mark.asyncio
async def test_docs_adapter_handles_processor_exception():
    failing_processor = MagicMock()
    failing_processor.process_query = AsyncMock(side_effect=RuntimeError("Vector index unavailable"))
    adapter = DocumentationSearchAdapter(query_processor=failing_processor)

    result = await adapter.execute(
        query="What is this?",
        doc_type="indexed",
        repo_id="repo-123",
    )
    assert result.success is False
    assert "Vector index unavailable" in result.error


@pytest.mark.asyncio
async def test_docs_adapter_none_query_processor_returns_clear_error():
    """
    Regression test: DocumentationSearchAdapter must return a descriptive
    ToolResult(success=False) when query_processor is None, not crash with
    AttributeError: 'NoneType' object has no attribute 'process_query'.
    """
    adapter = DocumentationSearchAdapter(query_processor=None)

    result = await adapter.execute(
        query="What is this?",
        doc_type="indexed",
        repo_id="repo-123",
    )
    assert result.success is False
    assert "not initialised" in result.error
