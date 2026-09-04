"""Unit tests for ReRanker scoring signals."""
from src.application.rag.reranker import ReRanker
from src.domain.models.rag import ParsedQuery, QueryIntent
from src.domain.models.chunk import SemanticChunk, SearchResult

def test_reranker_sorting_by_scores():
    # Setup test parsed query
    pq = ParsedQuery(
        original_query="where is the auth token validated?",
        rewritten_queries=["where is the auth token validated?"],
        intent=QueryIntent.SECURITY_REVIEW,
        detected_symbols=["validate_token"],
        detected_files=["auth.py"]
    )
    
    # Setup retrieved search results
    chunk_fn = SemanticChunk(
        id="1", repo_id="repo", file_path="src/auth.py", content="def validate_token(): pass",
        language="python", commit_hash="abc", symbol_name="validate_token", symbol_type="function"
    )
    chunk_test = SemanticChunk(
        id="2", repo_id="repo", file_path="tests/test_auth.py", content="def test_validate(): pass",
        language="python", commit_hash="abc", symbol_name="test_validate", symbol_type="function"
    )
    
    sr1 = SearchResult(chunk=chunk_fn, vector_score=0.85)
    sr2 = SearchResult(chunk=chunk_test, vector_score=0.85)  # Same vector score
    
    reranker = ReRanker()
    ranked = reranker.rerank([sr1, sr2], pq)
    
    # sr1 should be ranked higher due to file structure (src/auth.py vs tests/test_auth.py)
    # and explicit file name matching
    assert ranked[0].chunk_id == "1"
    assert ranked[1].chunk_id == "2"
    assert ranked[0].final_score > ranked[1].final_score
