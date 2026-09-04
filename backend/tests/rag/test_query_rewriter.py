"""Unit tests for Query Rewriter component."""
from src.application.rag.query_understanding import QueryUnderstanding
from src.application.rag.query_rewriter import QueryRewriter

def test_query_expansion():
    qu = QueryUnderstanding()
    rewriter = QueryRewriter()
    
    parsed = qu.classify_intent("where is login?")
    expanded = rewriter.rewrite(parsed)
    
    # Check that original is preserved
    assert expanded.rewritten_queries[0] == "where is login?"
    # Check that multiple sub-queries are generated
    assert len(expanded.rewritten_queries) > 1
    # Check symbol-focused sub-query exists
    assert any("login" in q for q in expanded.rewritten_queries)
