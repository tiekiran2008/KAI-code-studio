"""
AST-Aware & Structural Code Chunker
====================================
Transforms source files into fine-grained SemanticChunk domain objects for RAG:
- Symbol-level chunks: Uses PythonParser (tree-sitter) to extract classes, functions, methods
- Structural chunks: Sliding line-window chunks with overlap for full coverage of files, configs, and scripts
- Metadata preservation: Preserves repo_id, file_path, start_line, end_line, language, symbol info, and content hashes
- Size boundaries: Truncates / bounds chunks to ensure they fit within the embedding model token budget
"""
import hashlib
import uuid
from typing import List, Optional

from src.domain.models.chunk import SemanticChunk
from src.infrastructure.parsing.python_parser import PythonParser
from src.infrastructure.filesystem.file_filter import FileFilter


class CodeChunker:
    """AST-aware and sliding-window chunker producing SemanticChunk instances."""

    # Maximum characters per chunk to prevent embedding truncation (approx. 800-1000 tokens)
    MAX_CHUNK_CHARS: int = 4000
    # Sliding window chunk size in lines for structural chunking
    DEFAULT_WINDOW_LINES: int = 40
    # Overlap lines between adjacent windows
    DEFAULT_OVERLAP_LINES: int = 10

    def __init__(self, python_parser: Optional[PythonParser] = None):
        try:
            self.python_parser = python_parser or PythonParser()
        except Exception:
            self.python_parser = None

    @staticmethod
    def compute_content_hash(content: str) -> str:
        """Compute deterministic SHA-256 hash of chunk content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_chunk_id(repo_id: str, file_path: str, start_line: int, end_line: int, symbol_name: Optional[str] = None) -> str:
        """Generate deterministic, collision-resistant UUID for the chunk."""
        key = f"{repo_id}:{file_path}:{start_line}:{end_line}:{symbol_name or 'block'}"
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, key))

    def chunk_file(
        self,
        repo_id: str,
        file_path: str,
        content: str,
        commit_hash: str = "HEAD",
    ) -> List[SemanticChunk]:
        """
        Chunk a single file into SemanticChunk objects.
        Returns symbol-level chunks (if applicable) plus structural window chunks.
        """
        if not content or not content.strip():
            return []

        clean_path = file_path.replace("\\", "/")
        language = FileFilter.detect_language(clean_path)
        lines = content.splitlines()
        total_lines = len(lines)
        chunks: List[SemanticChunk] = []
        seen_ranges = set()

        # 1. AST Symbol Extraction for Python files
        if language == "python" and self.python_parser:
            try:
                symbols = self.python_parser.parse_symbols(content, clean_path)
                imports = self.python_parser.extract_imports(content)

                for sym in symbols:
                    if sym.start_line and sym.end_line and 1 <= sym.start_line <= total_lines:
                        end = min(sym.end_line, total_lines)
                        sym_slice = lines[sym.start_line - 1 : end]
                        sym_content = "\n".join(sym_slice).strip()

                        if sym_content:
                            # Bound content length
                            bounded_content = sym_content[: self.MAX_CHUNK_CHARS]
                            chunk_id = self.generate_chunk_id(
                                repo_id, clean_path, sym.start_line, end, sym.name
                            )
                            chunks.append(
                                SemanticChunk(
                                    id=chunk_id,
                                    repo_id=repo_id,
                                    file_path=clean_path,
                                    content=bounded_content,
                                    language=language,
                                    commit_hash=commit_hash,
                                    symbol_name=sym.name,
                                    symbol_type=sym.symbol_type,
                                    start_line=sym.start_line,
                                    end_line=end,
                                    imports=imports[:10] if imports else [],
                                )
                            )
                            seen_ranges.add((sym.start_line, end))
            except Exception:
                # If AST parsing fails on invalid syntax, fallback to structural chunking
                pass

        # 2. Structural Sliding Window Chunking (Full File Coverage)
        # If the file is small (<= 50 lines), create a single whole-file chunk
        if total_lines <= 50:
            file_content = content[: self.MAX_CHUNK_CHARS].strip()
            if file_content and (1, total_lines) not in seen_ranges:
                chunk_id = self.generate_chunk_id(repo_id, clean_path, 1, total_lines, "file_root")
                chunks.append(
                    SemanticChunk(
                        id=chunk_id,
                        repo_id=repo_id,
                        file_path=clean_path,
                        content=file_content,
                        language=language,
                        commit_hash=commit_hash,
                        start_line=1,
                        end_line=total_lines,
                    )
                )
        else:
            step = self.DEFAULT_WINDOW_LINES - self.DEFAULT_OVERLAP_LINES
            for start_idx in range(0, total_lines, step):
                end_idx = min(start_idx + self.DEFAULT_WINDOW_LINES, total_lines)
                window_lines = lines[start_idx:end_idx]
                window_content = "\n".join(window_lines).strip()

                if window_content:
                    start_line = start_idx + 1
                    end_line = end_idx
                    if (start_line, end_line) not in seen_ranges:
                        bounded_content = window_content[: self.MAX_CHUNK_CHARS]
                        chunk_id = self.generate_chunk_id(
                            repo_id, clean_path, start_line, end_line, f"block_{start_line}"
                        )
                        chunks.append(
                            SemanticChunk(
                                id=chunk_id,
                                repo_id=repo_id,
                                file_path=clean_path,
                                content=bounded_content,
                                language=language,
                                commit_hash=commit_hash,
                                start_line=start_line,
                                end_line=end_line,
                            )
                        )
                if end_idx >= total_lines:
                    break

        return chunks
