"""
Hybrid Retriever
================
Fans out to multiple retrieval strategies in parallel and merges the
results into a deduplicated candidate set for the re-ranker.

Strategies:
1. SemanticRetriever    — embedding similarity via Qdrant
2. SymbolSearcher       — exact/partial symbol_name payload filter
3. FileRetriever        — file_path filter from detected file hints
4. MultiQueryRetriever  — runs all rewritten sub-queries concurrently

All results are merged by chunk_id; the highest vector score per chunk
is kept. The union is returned unsorted (re-ranker handles ordering).
"""
import asyncio
from typing import List, Dict
import structlog

from src.domain.interfaces.rag import IRetriever
from src.domain.interfaces.embedding import IEmbeddingService
from src.domain.interfaces.vector_db import IVectorDB
from src.domain.models.rag import ParsedQuery
from src.domain.models.chunk import SearchResult, SemanticChunk

from src.core.logger import logger

_COLLECTION = "codebase_chunks"


def _raw_to_search_result(raw: Dict) -> SearchResult:
    """Convert a raw Qdrant payload dict → SearchResult domain object."""
    chunk = SemanticChunk(
        id=raw["id"],
        repo_id=raw.get("repo_id", ""),
        file_path=raw.get("file_path", ""),
        content=raw.get("content", ""),
        language=raw.get("language", ""),
        commit_hash=raw.get("commit_hash", ""),
        symbol_name=raw.get("symbol_name"),
        symbol_type=raw.get("symbol_type"),
        start_line=raw.get("start_line"),
        end_line=raw.get("end_line"),
        imports=raw.get("imports", []),
    )
    return SearchResult(chunk=chunk, vector_score=raw.get("score", 0.0))


class SemanticRetriever:
    """Pure embedding-similarity retrieval from Qdrant."""

    def __init__(self, embedding_service: IEmbeddingService, vector_db: IVectorDB) -> None:
        self._emb = embedding_service
        self._vdb = vector_db

    async def retrieve(
        self, query: str, repo_id: str, limit: int = 15
    ) -> List[SearchResult]:
        embedding = await asyncio.to_thread(self._emb.generate_embedding, query)
        raw = await asyncio.to_thread(
            self._vdb.search,
            _COLLECTION,
            embedding,
            {"repo_id": repo_id},
            limit,
        )
        return [_raw_to_search_result(r) for r in raw]


class SymbolSearcher:
    """
    Retrieves chunks whose symbol_name payload matches a detected symbol.
    Uses Qdrant full-text match. Falls back to an empty list gracefully.
    """

    def __init__(self, vector_db: IVectorDB) -> None:
        self._vdb = vector_db

    async def retrieve(
        self, symbols: List[str], repo_id: str
    ) -> List[SearchResult]:
        if not symbols:
            return []

        results: Dict[str, SearchResult] = {}
        for symbol in symbols[:5]:   # Cap at 5 symbols to avoid fan-out explosion
            try:
                raw = await asyncio.to_thread(
                    self._vdb.search,
                    _COLLECTION,
                    [0.0] * 384,    # dummy vector; we rely on the payload filter
                    {"repo_id": repo_id, "symbol_name": symbol},
                    limit=5,
                )
                for r in raw:
                    cid = str(r["id"])
                    if cid not in results:
                        results[cid] = _raw_to_search_result(r)
            except Exception as exc:
                logger.debug("symbol_search_skipped", symbol=symbol, error=str(exc))
        return list(results.values())


class FileRetriever:
    """Retrieves chunks filtered by detected file path hints."""

    def __init__(self, embedding_service: IEmbeddingService, vector_db: IVectorDB) -> None:
        self._emb = embedding_service
        self._vdb = vector_db

    async def retrieve(
        self, query: str, files: List[str], repo_id: str
    ) -> List[SearchResult]:
        if not files:
            return []
        embedding = await asyncio.to_thread(self._emb.generate_embedding, query)
        results: Dict[str, SearchResult] = {}
        for file_name in files[:3]:  # Cap at 3 files
            try:
                raw = await asyncio.to_thread(
                    self._vdb.search,
                    _COLLECTION,
                    embedding,
                    {"repo_id": repo_id, "file_path": file_name},
                    limit=8,
                )
                for r in raw:
                    cid = str(r["id"])
                    if cid not in results:
                        results[cid] = _raw_to_search_result(r)
            except Exception as exc:
                logger.debug("file_retrieval_skipped", file=file_name, error=str(exc))
        return list(results.values())


class HybridRetriever(IRetriever):
    """
    Orchestrates all retrieval strategies concurrently via asyncio.gather
    and merges results keeping the best vector_score per chunk_id.
    """

    def __init__(
        self,
        embedding_service: IEmbeddingService,
        vector_db: IVectorDB,
    ) -> None:
        self._semantic = SemanticRetriever(embedding_service, vector_db)
        self._symbol = SymbolSearcher(vector_db)
        self._file = FileRetriever(embedding_service, vector_db)

    async def retrieve(
        self,
        parsed_query: ParsedQuery,
        limit: int = 20,
    ) -> List[SearchResult]:
        """
        Parallel fan-out across all strategies, then merge by chunk_id.
        Sub-queries from the rewriter are also run concurrently.
        """
        repo_id = parsed_query.repo_id

        # Build coroutines for every rewritten sub-query
        sub_query_coros = [
            self._semantic.retrieve(q, repo_id, limit=10)
            for q in parsed_query.rewritten_queries
        ]

        # Add symbol and file strategies
        symbol_coro = self._symbol.retrieve(parsed_query.detected_symbols, repo_id)
        file_coro = self._file.retrieve(
            parsed_query.original_query, parsed_query.detected_files, repo_id
        )

        all_coros = sub_query_coros + [symbol_coro, file_coro]
        all_results: List[List[SearchResult]] = await asyncio.gather(
            *all_coros, return_exceptions=False
        )

        # Merge: keep best vector_score per chunk_id
        merged: Dict[str, SearchResult] = {}
        for batch in all_results:
            for sr in batch:
                cid = sr.chunk.id
                if cid not in merged or sr.vector_score > merged[cid].vector_score:
                    merged[cid] = sr

        logger.info(
            "hybrid_retrieval_complete",
            total_unique=len(merged),
            sub_queries=len(parsed_query.rewritten_queries),
        )
        return list(merged.values())
