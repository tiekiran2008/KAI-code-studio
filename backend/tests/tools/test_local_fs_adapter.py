"""
Unit Tests — Local File System Adapter
======================================
Tests safe reads, dir listing, search, and path traversal protection.
"""
import pytest
from pathlib import Path

from src.infrastructure.tools.adapters.local_fs import LocalFileSystemAdapter


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    
    (root / "config.json").write_text('{"env": "test"}')
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('hello')")
    
    return root

@pytest.fixture
def adapter(workspace):
    return LocalFileSystemAdapter(str(workspace))


@pytest.mark.asyncio
async def test_read_file_success(adapter):
    result = await adapter.execute(action="read_file", path="config.json")
    assert result.success is True
    assert "test" in result.data["content"]


@pytest.mark.asyncio
async def test_list_dir_success(adapter):
    result = await adapter.execute(action="list_dir", path="")
    assert result.success is True
    assert "config.json" in result.data["items"]
    assert "src" in result.data["items"]


@pytest.mark.asyncio
async def test_search_success(adapter):
    result = await adapter.execute(action="search", path="", pattern="**/*.py")
    assert result.success is True
    # Normalize paths for assertion (Windows/Linux)
    normalized_matches = [m.replace("\\", "/") for m in result.data["matches"]]
    assert "src/main.py" in normalized_matches


@pytest.mark.asyncio
async def test_path_traversal_protection(adapter):
    # Attempt to read a file outside the workspace using ../
    result = await adapter.execute(action="read_file", path="../outside.txt")
    assert result.success is False
    assert "Path traversal detected or out of workspace bound" in result.error


@pytest.mark.asyncio
async def test_file_not_found(adapter):
    result = await adapter.execute(action="read_file", path="missing.txt")
    assert result.success is False
    assert "File not found" in result.error
