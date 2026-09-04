from src.application.services.ranking import RankingService
from src.domain.models.chunk import SearchResult, SemanticChunk

def test_ranking_service_prioritizes_classes_over_functions():
    chunk1 = SemanticChunk("1", "repo", "file.py", "def a(): pass", "python", "hash", symbol_type="function")
    chunk2 = SemanticChunk("2", "repo", "file.py", "class A: pass", "python", "hash", symbol_type="class")
    
    res1 = SearchResult(chunk=chunk1, vector_score=0.9)
    res2 = SearchResult(chunk=chunk2, vector_score=0.9) # Identical vector score
    
    ranking_service = RankingService()
    ranked = ranking_service.apply_heuristics([res1, res2])
    
    # Class should win due to symbol importance heuristic
    assert ranked[0].chunk.id == "2"
    assert ranked[1].chunk.id == "1"
