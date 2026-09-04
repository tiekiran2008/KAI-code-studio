"""Unit tests for Response Validator component."""
from src.application.rag.response_validator import ResponseValidator
from src.domain.models.rag import RerankedChunk

def test_response_validator_grounding():
    chunk = RerankedChunk(
        chunk_id="c1", repo_id="repo", file_path="auth.py", content="def validate_session_token(token): return True",
        language="python", commit_hash="abc", symbol_name="validate_session_token", symbol_type="function",
        start_line=1, end_line=5, embedding_score=0.9
    )
    
    val = ResponseValidator()
    
    # Grounded answer using terms from chunk
    res = val.validate("This function validate_session_token validates the user session token and returns True.", [chunk])
    assert res.is_valid is True
    assert res.confidence > 0.5
    
    # Hallucinated answer using ungrounded terms
    res_hallucinated = val.validate("We use a completely custom algorithm called SuperSecureCrypto to encrypt passwords.", [chunk])
    assert res_hallucinated.is_valid is False
    assert res_hallucinated.confidence < 0.35
