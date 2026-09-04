from typing import List
from src.domain.models.chunk import SearchResult

class RankingService:
    def rank_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Sorts search results by their composite final score."""
        return sorted(results, key=lambda x: x.final_score, reverse=True)

    def apply_heuristics(self, results: List[SearchResult], exact_path: str = None) -> List[SearchResult]:
        """Modifies component scores based on heuristics like symbol importance and exact path matches."""
        for res in results:
            # 1. Symbol importance
            if res.chunk.symbol_type == "class":
                res.symbol_importance = 1.0
            elif res.chunk.symbol_type == "function":
                res.symbol_importance = 0.8
            else:
                res.symbol_importance = 0.5
                
            # 2. Metadata score (exact path match boost)
            if exact_path and res.chunk.file_path == exact_path:
                res.metadata_score = 1.0
                
            res.recency_score = 1.0
            
        return self.rank_results(results)
