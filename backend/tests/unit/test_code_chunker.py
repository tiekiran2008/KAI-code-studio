import pytest
from src.infrastructure.parsing.code_chunker import CodeChunker


def test_code_chunker_extracts_python_ast_symbols():
    chunker = CodeChunker()
    python_code = """
import os
import sys

class UserManager:
    def __init__(self, db_url: str):
        self.db_url = db_url

    def authenticate_user(self, email: str, secret: str) -> bool:
        if not email or not secret:
            return False
        return True

def standalone_helper(x: int) -> int:
    return x * 2
"""
    chunks = chunker.chunk_file(
        repo_id="test-repo-123",
        file_path="src/users/manager.py",
        content=python_code,
        commit_hash="commit-abc",
    )

    assert len(chunks) > 0

    # Verify symbol-level chunks exist
    symbols = {c.symbol_name for c in chunks if c.symbol_name}
    assert "UserManager" in symbols or "authenticate_user" in symbols or "standalone_helper" in symbols

    for chunk in chunks:
        assert chunk.repo_id == "test-repo-123"
        assert chunk.file_path == "src/users/manager.py"
        assert chunk.language == "python"
        assert chunk.start_line >= 1
        assert chunk.end_line >= chunk.start_line


def test_code_chunker_handles_non_python_files():
    chunker = CodeChunker()
    typescript_code = """
export interface UserProfile {
  id: string;
  name: string;
  email: string;
}

export const fetchUserProfile = async (id: string): Promise<UserProfile> => {
  const res = await fetch(`/api/users/${id}`);
  return res.json();
};
"""
    chunks = chunker.chunk_file(
        repo_id="test-repo-456",
        file_path="frontend/src/api/users.ts",
        content=typescript_code,
    )

    assert len(chunks) >= 1
    assert chunks[0].repo_id == "test-repo-456"
    assert chunks[0].language == "typescript"
    assert "fetchUserProfile" in chunks[0].content


def test_code_chunker_bounds_large_content():
    chunker = CodeChunker()
    huge_content = "def test_func():\n" + ("    x = 1\n" * 1000)
    chunks = chunker.chunk_file(
        repo_id="test-repo-789",
        file_path="src/huge.py",
        content=huge_content,
    )

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.content) <= CodeChunker.MAX_CHUNK_CHARS + 100
