"""Unit tests for Query Understanding component."""
from src.application.rag.query_understanding import QueryUnderstanding
from src.domain.models.rag import QueryIntent

def test_intent_classification():
    qu = QueryUnderstanding()
    
    # Explain code
    res = qu.classify_intent("Explain the user processing flow and show how it works")
    assert res.intent == QueryIntent.EXPLAIN_CODE
    
    # Find implementation
    res = qu.classify_intent("where is the login handler function defined?")
    assert res.intent == QueryIntent.FIND_IMPLEMENTATION
    
    # Debug issue
    res = qu.classify_intent("Why is my code throwing a KeyError during validation?")
    assert res.intent == QueryIntent.DEBUG_ISSUE
    
    # Performance review
    res = qu.classify_intent("How can I optimize this slow database query?")
    assert res.intent == QueryIntent.PERFORMANCE_REVIEW

def test_symbol_and_file_extraction():
    qu = QueryUnderstanding()
    res = qu.classify_intent("Find where UserAuthService class is defined in auth_client.py")
    
    assert "UserAuthService" in res.detected_symbols
    assert "auth_client.py" in res.detected_files
    assert "python" in res.language_hints
