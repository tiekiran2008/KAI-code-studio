"""
Context Builder
===============
Merges re-ranked chunks into an optimised, deduplicated context window
ready for the prompt builder.

Responsibilities:
1. Deduplication     — drop chunks sharing the same chunk_id.
2. Adjacent merge    — merge overlapping line ranges in the same file to
                       avoid presenting the same code twice in slightly
                       different windows.
3. Token budgeting   — truncate lowest-scoring chunks to stay within the
                       configured token limit (estimated at ~4 chars/token).
4. Formatting        — wrap each chunk in a structured header containing
                       file path, line range, symbol name, and language.

Token estimation uses a simple character-based heuristic (4 chars ≈ 1 token)
to avoid an LLM API round-trip on the hot path. The LLM provider can still
count tokens accurately during prompt construction.
"""
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

from src.domain.interfaces.rag import IContextBuilder
from src.domain.models.rag import ContextWindow, RerankedChunk
from src.core.logger import logger

_CHARS_PER_TOKEN = 4           # Rough average for code


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _chunk_header(chunk: RerankedChunk) -> str:
    """Build the structured header prepended to each chunk in the context."""
    parts = [f"// FILE: {chunk.file_path}"]
    if chunk.start_line and chunk.end_line:
        parts.append(f"(lines {chunk.start_line}–{chunk.end_line})")
    if chunk.symbol_type and chunk.symbol_name:
        parts.append(f"[{chunk.symbol_type}: {chunk.symbol_name}]")
    elif chunk.symbol_type:
        parts.append(f"[{chunk.symbol_type}]")
    if chunk.language:
        parts.append(f"| lang: {chunk.language}")
    parts.append(f"| score: {chunk.final_score:.3f}")
    return " ".join(parts)


def _ranges_overlap(a_start: int, a_end: int, b_start: int, b_end: int, tolerance: int = 5) -> bool:
    """True if two line ranges overlap or are within `tolerance` lines of each other."""
    return not (a_end + tolerance < b_start or b_end + tolerance < a_start)


class ContextBuilder(IContextBuilder):
    """
    Produces an optimised ContextWindow from a list of RerankedChunks.

    Workflow:
    1. Deduplicate by chunk_id.
    2. Group chunks by file_path.
    3. Within each file, merge chunks whose line ranges overlap.
    4. Apply token budget — drop lowest-scoring chunks first.
    5. Format into a single context string with structured headers.
    """

    def build_context(
        self,
        chunks: List[RerankedChunk],
        token_budget: int = 12_000,
    ) -> ContextWindow:
        # --- Step 1: Deduplicate by chunk_id ---
        seen_ids: set = set()
        unique_chunks: List[RerankedChunk] = []
        for chunk in chunks:
            if chunk.chunk_id not in seen_ids:
                seen_ids.add(chunk.chunk_id)
                unique_chunks.append(chunk)

        # --- Step 2: Group by file path ---
        by_file: Dict[str, List[RerankedChunk]] = defaultdict(list)
        for chunk in unique_chunks:
            by_file[chunk.file_path].append(chunk)

        # --- Step 3: Merge adjacent/overlapping line ranges within each file ---
        merged_chunks: List[RerankedChunk] = []
        for file_path, file_chunks in by_file.items():
            # Sort by start line for merging
            sortable = sorted(
                file_chunks,
                key=lambda c: (c.start_line or 0),
            )
            merged = self._merge_overlapping(sortable)
            merged_chunks.extend(merged)

        # Sort globally by final_score descending for token budget trimming
        merged_chunks.sort(key=lambda c: c.final_score, reverse=True)

        # --- Step 4: Token budget enforcement ---
        budgeted_chunks: List[RerankedChunk] = []
        used_tokens = 0
        truncated = False

        for chunk in merged_chunks:
            header = _chunk_header(chunk)
            block = f"{header}\n```{chunk.language}\n{chunk.content}\n```"
            chunk_tokens = _estimate_tokens(block)

            if used_tokens + chunk_tokens <= token_budget:
                budgeted_chunks.append(chunk)
                used_tokens += chunk_tokens
            else:
                truncated = True
                logger.debug("context_budget_truncation", dropped_chunk=chunk.chunk_id)

        # --- Step 5: Format final context string ---
        context_parts: List[str] = []
        final_file_map: Dict[str, List[RerankedChunk]] = defaultdict(list)

        for chunk in budgeted_chunks:
            header = _chunk_header(chunk)
            block = f"{header}\n```{chunk.language}\n{chunk.content}\n```"
            context_parts.append(block)
            final_file_map[chunk.file_path].append(chunk)

        formatted_context = "\n\n---\n\n".join(context_parts)

        logger.info(
            "context_built",
            total_chunks=len(budgeted_chunks),
            estimated_tokens=used_tokens,
            truncated=truncated,
            unique_files=len(final_file_map),
        )

        return ContextWindow(
            chunks=budgeted_chunks,
            total_tokens=used_tokens,
            formatted_context=formatted_context,
            file_map=dict(final_file_map),
            token_budget=token_budget,
            truncated=truncated,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _merge_overlapping(self, chunks: List[RerankedChunk]) -> List[RerankedChunk]:
        """
        Merge chunks in the same file whose line ranges overlap or are
        within 5 lines of each other to avoid duplicate context.
        Returns the merged list (highest score wins for the merged chunk).
        """
        if not chunks:
            return []

        result: List[RerankedChunk] = []
        current = chunks[0]

        for next_chunk in chunks[1:]:
            a_start = current.start_line or 0
            a_end = current.end_line or 0
            b_start = next_chunk.start_line or 0
            b_end = next_chunk.end_line or 0

            if a_start > 0 and b_start > 0 and _ranges_overlap(a_start, a_end, b_start, b_end):
                # Merge: extend the current chunk's range and content
                merged_content = (
                    current.content
                    if current.embedding_score >= next_chunk.embedding_score
                    else next_chunk.content + "\n" + current.content
                )
                # Keep the chunk with the better embedding score but extend line range
                winner = current if current.embedding_score >= next_chunk.embedding_score else next_chunk
                merged = RerankedChunk(
                    chunk_id=winner.chunk_id,
                    repo_id=winner.repo_id,
                    file_path=winner.file_path,
                    content=merged_content,
                    language=winner.language,
                    commit_hash=winner.commit_hash,
                    symbol_name=winner.symbol_name,
                    symbol_type=winner.symbol_type,
                    start_line=min(a_start, b_start),
                    end_line=max(a_end, b_end),
                    imports=list(set(current.imports + next_chunk.imports)),
                    embedding_score=max(current.embedding_score, next_chunk.embedding_score),
                    symbol_importance_score=max(
                        current.symbol_importance_score, next_chunk.symbol_importance_score
                    ),
                    structure_score=max(current.structure_score, next_chunk.structure_score),
                    file_relevance_score=max(
                        current.file_relevance_score, next_chunk.file_relevance_score
                    ),
                    dependency_score=max(current.dependency_score, next_chunk.dependency_score),
                    metadata_score=max(current.metadata_score, next_chunk.metadata_score),
                )
                current = merged
            else:
                result.append(current)
                current = next_chunk

        result.append(current)
        return result
