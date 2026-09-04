"""Unit tests for Context Builder component."""
from src.application.rag.context_builder import ContextBuilder
from src.domain.models.rag import RerankedChunk

def test_context_builder_dedup_and_merge():
    # Setup overlapping and duplicate chunks
    c1 = RerankedChunk(
        chunk_id="c1", repo_id="repo", file_path="auth.py", content="def login():\n    pass",
        language="python", commit_hash="abc", symbol_name="login", symbol_type="function",
        start_line=10, end_line=15, embedding_score=0.9
    )
    c2 = RerankedChunk(
        chunk_id="c2", repo_id="repo", file_path="auth.py", content="    validate()\n    return True",
        language="python", commit_hash="abc", symbol_name="login", symbol_type="function",
        start_line=14, end_line=20, embedding_score=0.8
    )
    
    cb = ContextBuilder()
    window = cb.build_context([c1, c2], token_budget=1000)
    
    # Verify adjacent line range merge was executed
    assert len(window.chunks) == 1
    assert window.chunks[0].start_line == 10
    assert window.chunks[0].end_line == 20
