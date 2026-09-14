"""
Unit Tests — GitHub Tool Adapter
================================
Tests HTTP integration using an httpx mocked transport.
"""
import pytest
import httpx
from unittest.mock import patch, MagicMock

from src.infrastructure.tools.adapters.github import GitHubToolAdapter


@pytest.fixture
def adapter():
    return GitHubToolAdapter(github_token="fake_token")


@pytest.mark.asyncio
async def test_execute_branches_success(adapter):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"name": "main"}, {"name": "dev"}]

    with patch("httpx.AsyncClient.get", return_value=mock_resp) as mock_get:
        result = await adapter.execute(owner="test", repo="repo", action="branches")
        
        assert result.success is True
        assert len(result.data) == 2
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "https://api.github.com/repos/test/repo/branches" in args[0]
        assert kwargs["headers"]["Authorization"] == "Bearer fake_token"


@pytest.mark.asyncio
async def test_execute_invalid_action(adapter):
    result = await adapter.execute(owner="test", repo="repo", action="invalid_action")
    assert result.success is False
    assert "Invalid action" in result.error


@pytest.mark.asyncio
async def test_execute_http_error(adapter):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "Not Found"

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        result = await adapter.execute(owner="test", repo="repo", action="commits")
        
        assert result.success is False
        assert "not found" in result.error.lower()

