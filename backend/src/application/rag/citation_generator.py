"""
Citation Generator
==================
Parses the LLM's answer to extract inline citation markers and maps them
back to source chunks, building structured Citation domain objects.

Expected citation format (instructed in system prompt):
    [FILE: path/to/file.py, LINES: 10-45, SYMBOL: ClassName]

Additionally:
- Any code identifier in the answer that matches a chunk's symbol_name
  gets an implicit citation with moderate confidence.
- Chunks most similar to the answer content receive a residual citation.
"""
import re
from typing import List, Dict, Set

from src.domain.interfaces.rag import ICitationGenerator
from src.domain.models.rag import Citation, RerankedChunk
from src.core.logger import logger

# Regex for explicit citation markers injected by the LLM
_CITATION_RE = re.compile(
    r"\[FILE:\s*(?P<file>[^\],]+?)(?:,\s*LINES:\s*(?P<lines>\d+(?:-\d+)?))?(?:,\s*SYMBOL:\s*(?P<symbol>[^\]]+))?\]",
    re.IGNORECASE,
)

_LINE_RANGE_RE = re.compile(r"(\d+)(?:-(\d+))?")


def _parse_line_range(lines_str: str):
    """Parse '10-45' or '10' → (10, 45) or (10, 10)."""
    m = _LINE_RANGE_RE.match(lines_str or "")
    if not m:
        return None, None
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else start
    return start, end


def _build_chunk_index(chunks: List[RerankedChunk]) -> Dict[str, RerankedChunk]:
    """Build a lookup of file_path → best chunk for that file."""
    index: Dict[str, RerankedChunk] = {}
    for chunk in chunks:
        if chunk.file_path not in index or chunk.final_score > index[chunk.file_path].final_score:
            index[chunk.file_path] = chunk
    return index


def _build_symbol_index(chunks: List[RerankedChunk]) -> Dict[str, RerankedChunk]:
    """Build a lookup of symbol_name.lower() → chunk."""
    index: Dict[str, RerankedChunk] = {}
    for chunk in chunks:
        if chunk.symbol_name:
            index[chunk.symbol_name.lower()] = chunk
    return index


class CitationGenerator(ICitationGenerator):
    """
    Generates structured citations from:
    1. Explicit [FILE: ...] markers in the LLM answer.
    2. Symbol names in the answer that match retrieved chunks.
    3. Residual citations for the top-scored chunks used in the answer.
    """

    def generate(
        self,
        answer: str,
        chunks: List[RerankedChunk],
    ) -> List[Citation]:
        citations: List[Citation] = []
        cited_chunk_ids: Set[str] = set()

        file_index = _build_chunk_index(chunks)
        symbol_index = _build_symbol_index(chunks)

        # --- Pass 1: Explicit citation markers ---
        for match in _CITATION_RE.finditer(answer):
            file_path = match.group("file").strip() if match.group("file") else None
            lines_str = match.group("lines") if match.group("lines") else None
            symbol = match.group("symbol").strip() if match.group("symbol") else None

            start_line, end_line = _parse_line_range(lines_str) if lines_str else (None, None)

            # Find best matching chunk for this citation
            matched_chunk = None
            if file_path:
                # Try exact match, then partial match
                matched_chunk = file_index.get(file_path)
                if not matched_chunk:
                    for fp, c in file_index.items():
                        if file_path.lower() in fp.lower():
                            matched_chunk = c
                            break

            # If symbol found, check symbol index as fallback
            if not matched_chunk and symbol:
                matched_chunk = symbol_index.get(symbol.lower())

            confidence = 0.95 if matched_chunk else 0.60

            citation = Citation(
                file_path=file_path or (matched_chunk.file_path if matched_chunk else "unknown"),
                repo_path=matched_chunk.file_path if matched_chunk else (file_path or "unknown"),
                class_name=symbol if symbol and (not matched_chunk or matched_chunk.symbol_type in ("class", "interface")) else (matched_chunk.symbol_name if matched_chunk else None),
                function_name=symbol if symbol and matched_chunk and matched_chunk.symbol_type in ("function", "method") else None,
                start_line=start_line or (matched_chunk.start_line if matched_chunk else None),
                end_line=end_line or (matched_chunk.end_line if matched_chunk else None),
                symbol_type=matched_chunk.symbol_type if matched_chunk else None,
                confidence=confidence,
                chunk_id=matched_chunk.chunk_id if matched_chunk else "",
            )
            citations.append(citation)
            if matched_chunk:
                cited_chunk_ids.add(matched_chunk.chunk_id)

        # --- Pass 2: Implicit citations via symbol name matching ---
        answer_lower = answer.lower()
        for sym_name, chunk in symbol_index.items():
            if chunk.chunk_id in cited_chunk_ids:
                continue
            # Only cite if the symbol name appears verbatim in the answer
            if sym_name in answer_lower and len(sym_name) >= 4:
                citations.append(Citation(
                    file_path=chunk.file_path,
                    repo_path=chunk.file_path,
                    class_name=chunk.symbol_name if chunk.symbol_type in ("class", "interface") else None,
                    function_name=chunk.symbol_name if chunk.symbol_type in ("function", "method") else None,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    symbol_type=chunk.symbol_type,
                    confidence=0.75,
                    chunk_id=chunk.chunk_id,
                ))
                cited_chunk_ids.add(chunk.chunk_id)

        # --- Pass 3: Residual top-chunk citations (up to 3) ---
        residual_count = 0
        for chunk in sorted(chunks, key=lambda c: c.final_score, reverse=True):
            if chunk.chunk_id in cited_chunk_ids:
                continue
            if residual_count >= 3:
                break
            citations.append(Citation(
                file_path=chunk.file_path,
                repo_path=chunk.file_path,
                class_name=chunk.symbol_name if chunk.symbol_type in ("class", "interface") else None,
                function_name=chunk.symbol_name if chunk.symbol_type in ("function", "method") else None,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                symbol_type=chunk.symbol_type,
                confidence=0.50,
                chunk_id=chunk.chunk_id,
            ))
            cited_chunk_ids.add(chunk.chunk_id)
            residual_count += 1

        # Deduplicate by (file_path, start_line)
        seen: Set[tuple] = set()
        unique: List[Citation] = []
        for c in citations:
            key = (c.file_path, c.start_line)
            if key not in seen:
                seen.add(key)
                unique.append(c)

        logger.info(
            "citations_generated",
            total=len(unique),
            explicit=sum(1 for c in unique if c.confidence >= 0.90),
            implicit=sum(1 for c in unique if 0.70 <= c.confidence < 0.90),
            residual=sum(1 for c in unique if c.confidence < 0.70),
        )
        return unique
