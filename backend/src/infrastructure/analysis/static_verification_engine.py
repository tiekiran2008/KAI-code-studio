"""
Static Verification Engine (Tier-1)
===================================
In-memory, deterministic syntax and static text verification engine.

CRITICAL SECURITY RULES:
- Zero repository code execution.
- Zero subprocess / os.system / shell / eval / exec.
- Zero network calls, zero file mutations.
- Operates strictly on source code text in-memory.
"""
import ast
import hashlib
import re
import time
from pathlib import Path
from typing import Optional, List, Tuple

from src.domain.entities.verification import (
    VerificationStatus,
    CheckStatus,
    VerificationCheck,
    StaticVerificationResult,
)


class StaticVerificationEngine:
    """Deterministic in-memory syntax and static check verifier."""

    # Unresolved conflict markers regex
    _CONFLICT_MARKERS = [
        re.compile(r"^<{7}(?:\s.*)?$", re.MULTILINE),
        re.compile(r"^={7}$", re.MULTILINE),
        re.compile(r"^>{7}(?:\s.*)?$", re.MULTILINE),
    ]

    def __init__(self) -> None:
        self._ts_parsers: dict = {}
        self._init_tree_sitter_parsers()

    def _init_tree_sitter_parsers(self) -> None:
        """Attempt safe in-memory initialisation of tree-sitter parsers."""
        try:
            from tree_sitter import Language, Parser

            # JavaScript
            try:
                import tree_sitter_javascript as ts_js
                js_lang = Language(ts_js.language())
                self._ts_parsers["javascript"] = Parser(js_lang)
            except Exception:
                pass

            # TypeScript
            try:
                import tree_sitter_typescript as ts_ts
                ts_lang = Language(ts_ts.language_typescript())
                self._ts_parsers["typescript"] = Parser(ts_lang)
            except Exception:
                pass

            # Java
            try:
                import tree_sitter_java as ts_java
                java_lang = Language(ts_java.language())
                self._ts_parsers["java"] = Parser(java_lang)
            except Exception:
                pass

        except Exception:
            # Tree-sitter not available in current environment; graceful degradation
            pass

    def detect_language(self, file_path: str, hint_language: Optional[str] = None) -> str:
        """Normalise or infer language name from file extension and hints."""
        if hint_language:
            hint_lower = hint_language.strip().lower()
            if hint_lower in ("py", "python"):
                return "python"
            if hint_lower in ("js", "javascript", "jsx"):
                return "javascript"
            if hint_lower in ("ts", "typescript", "tsx"):
                return "typescript"
            if hint_lower in ("java",):
                return "java"
            if hint_lower in ("go", "golang"):
                return "go"
            if hint_lower in ("rs", "rust"):
                return "rust"
            if hint_lower in ("rb", "ruby"):
                return "ruby"
            if hint_lower in ("php",):
                return "php"
            if hint_lower in ("c", "cpp", "c++", "h", "hpp"):
                return "c/c++"

        ext = Path(file_path).suffix.lower() if file_path else ""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".mjs": "javascript",
            ".cjs": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".mts": "typescript",
            ".cts": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".c": "c/c++",
            ".cpp": "c/c++",
            ".cc": "c/c++",
            ".h": "c/c++",
            ".hpp": "c/c++",
        }
        return ext_map.get(ext, hint_language.lower() if hint_language else "unknown")

    def verify_source(
        self,
        source_text: str,
        file_path: str,
        hint_language: Optional[str] = None,
        expected_hash: Optional[str] = None,
    ) -> StaticVerificationResult:
        """Run all deterministic Tier-1 static verification checks on source text.

        Parameters
        ----------
        source_text : str
            Full source text of the target file to verify.
        file_path : str
            Relative file path (for language detection and reporting).
        hint_language : Optional[str]
            Optional language hint from metadata or detection.
        expected_hash : Optional[str]
            Optional SHA-256 hash expected for the file content.

        Returns
        -------
        StaticVerificationResult
            Structured verification result.
        """
        start_time = time.perf_counter()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Compute SHA-256 hash of verified source
        verified_bytes = source_text.encode("utf-8") if isinstance(source_text, str) else b""
        verified_hash = hashlib.sha256(verified_bytes).hexdigest()

        language = self.detect_language(file_path, hint_language)
        checks: List[VerificationCheck] = []
        errors: List[str] = []
        warnings: List[str] = []

        # -------------------------------------------------------------
        # Check 1: Non-Empty Source Check
        # -------------------------------------------------------------
        if not source_text or not source_text.strip():
            checks.append(
                VerificationCheck(
                    name="non_empty_source",
                    status=CheckStatus.FAILED,
                    message="Source code is empty or contains whitespace only",
                )
            )
            errors.append("Source file is empty")
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return StaticVerificationResult(
                status=VerificationStatus.FAILED,
                language=language,
                verified_at=now_iso,
                verified_hash=verified_hash,
                duration_ms=duration_ms,
                checks=checks,
                errors=errors,
                warnings=warnings,
                message="Verification failed: source code is empty",
            )

        checks.append(
            VerificationCheck(
                name="non_empty_source",
                status=CheckStatus.PASSED,
                message="Source code is non-empty",
            )
        )

        # -------------------------------------------------------------
        # Check 2: Conflict Markers Check
        # -------------------------------------------------------------
        has_conflict, conflict_line, conflict_desc = self._check_conflict_markers(source_text)
        if has_conflict:
            checks.append(
                VerificationCheck(
                    name="conflict_markers",
                    status=CheckStatus.FAILED,
                    message=f"Unresolved merge conflict marker detected: {conflict_desc}",
                    line_number=conflict_line,
                )
            )
            errors.append(f"Conflict marker at line {conflict_line}: {conflict_desc}")
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return StaticVerificationResult(
                status=VerificationStatus.FAILED,
                language=language,
                verified_at=now_iso,
                verified_hash=verified_hash,
                duration_ms=duration_ms,
                checks=checks,
                errors=errors,
                warnings=warnings,
                message=f"Verification failed: unresolved merge conflict markers detected at line {conflict_line}",
            )

        checks.append(
            VerificationCheck(
                name="conflict_markers",
                status=CheckStatus.PASSED,
                message="No unresolved merge conflict markers detected",
            )
        )

        # -------------------------------------------------------------
        # Check 3: Language-Specific In-Memory Syntax Parsing
        # -------------------------------------------------------------
        if language == "python":
            syntax_check = self._verify_python_syntax(source_text)
            checks.append(syntax_check)
            if syntax_check.status == CheckStatus.FAILED:
                errors.append(syntax_check.message)
                overall_status = VerificationStatus.FAILED
                summary_msg = f"Python syntax verification failed: {syntax_check.message}"
            else:
                overall_status = VerificationStatus.PASSED
                summary_msg = "Configured Tier-1 static/syntax checks passed (in-memory AST validation)"

        elif language in ("javascript", "typescript"):
            parser = self._ts_parsers.get(language) or self._ts_parsers.get("javascript")
            if parser:
                syntax_check = self._verify_treesitter_syntax(parser, source_text, language)
                checks.append(syntax_check)
                if syntax_check.status == CheckStatus.FAILED:
                    errors.append(syntax_check.message)
                    overall_status = VerificationStatus.FAILED
                    summary_msg = f"{language.title()} syntax verification failed: {syntax_check.message}"
                else:
                    overall_status = VerificationStatus.PASSED
                    summary_msg = f"Configured Tier-1 static/syntax checks passed (in-memory {language.title()} tree-sitter validation)"
            else:
                checks.append(
                    VerificationCheck(
                        name="syntax_parser",
                        status=CheckStatus.UNSUPPORTED,
                        message=f"Tree-sitter parser not available for {language}; syntax check unsupported in this environment",
                    )
                )
                warnings.append(f"Syntax validation not available for {language}")
                overall_status = VerificationStatus.UNSUPPORTED
                summary_msg = f"Tier-1 static syntax check is unsupported for {language}; manual review recommended"

        elif language == "java":
            parser = self._ts_parsers.get("java")
            if parser:
                syntax_check = self._verify_treesitter_syntax(parser, source_text, "java")
                checks.append(syntax_check)
                if syntax_check.status == CheckStatus.FAILED:
                    errors.append(syntax_check.message)
                    overall_status = VerificationStatus.FAILED
                    summary_msg = f"Java syntax verification failed: {syntax_check.message}"
                else:
                    overall_status = VerificationStatus.PASSED
                    summary_msg = "Configured Tier-1 static/syntax checks passed (in-memory Java tree-sitter validation)"
            else:
                checks.append(
                    VerificationCheck(
                        name="syntax_parser",
                        status=CheckStatus.UNSUPPORTED,
                        message="Tree-sitter parser not available for Java; syntax check unsupported in this environment",
                    )
                )
                warnings.append("Syntax validation not available for Java")
                overall_status = VerificationStatus.UNSUPPORTED
                summary_msg = "Tier-1 static syntax check is unsupported for Java; manual review recommended"

        else:
            # Unsupported / unknown language — NEVER return false PASS
            checks.append(
                VerificationCheck(
                    name="syntax_parser",
                    status=CheckStatus.UNSUPPORTED,
                    message=f"Static syntax verification is not natively supported for language '{language}'",
                )
            )
            warnings.append(f"Language '{language}' unsupported for Tier-1 syntax verification")
            overall_status = VerificationStatus.UNSUPPORTED
            summary_msg = f"Tier-1 static syntax verification is unsupported for language '{language}'; manual review recommended"

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        return StaticVerificationResult(
            status=overall_status,
            language=language,
            verified_at=now_iso,
            verified_hash=verified_hash,
            duration_ms=duration_ms,
            checks=checks,
            errors=errors,
            warnings=warnings,
            message=summary_msg,
        )

    def _check_conflict_markers(self, source_text: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """Detect unresolved merge conflict markers line by line."""
        lines = source_text.splitlines()
        for idx, line in enumerate(lines, 1):
            if line.startswith("<<<<<<<"):
                return True, idx, "<<<<<<< (conflict start marker)"
            if line.startswith("======="):
                return True, idx, "======= (conflict separator marker)"
            if line.startswith(">>>>>>>"):
                return True, idx, ">>>>>>> (conflict end marker)"
        return False, None, None

    def _verify_python_syntax(self, source_text: str) -> VerificationCheck:
        """In-memory AST parsing of Python source without code execution."""
        try:
            ast.parse(source_text, filename="<string>")
            return VerificationCheck(
                name="syntax_parser",
                status=CheckStatus.PASSED,
                message="Python AST syntax verification passed",
            )
        except SyntaxError as exc:
            # Sanitize error message to prevent host path leaks
            safe_msg = exc.msg or "Syntax error"
            return VerificationCheck(
                name="syntax_parser",
                status=CheckStatus.FAILED,
                message=f"Python syntax error: {safe_msg}",
                line_number=exc.lineno,
                column=exc.offset,
            )
        except Exception as exc:
            return VerificationCheck(
                name="syntax_parser",
                status=CheckStatus.FAILED,
                message=f"Python parse error: {type(exc).__name__}",
            )

    def _verify_treesitter_syntax(self, parser, source_text: str, lang_name: str) -> VerificationCheck:
        """In-memory Tree-sitter CST parsing to detect syntax error nodes."""
        try:
            tree = parser.parse(bytes(source_text, "utf-8"))
            if tree.root_node.has_error:
                # Find first error node
                err_line, err_col = self._find_first_error_node(tree.root_node)
                return VerificationCheck(
                    name="syntax_parser",
                    status=CheckStatus.FAILED,
                    message=f"{lang_name.title()} syntax error detected by tree-sitter CST parser",
                    line_number=err_line,
                    column=err_col,
                )
            return VerificationCheck(
                name="syntax_parser",
                status=CheckStatus.PASSED,
                message=f"{lang_name.title()} tree-sitter syntax verification passed",
            )
        except Exception as exc:
            return VerificationCheck(
                name="syntax_parser",
                status=CheckStatus.FAILED,
                message=f"{lang_name.title()} parser error: {type(exc).__name__}",
            )

    def _find_first_error_node(self, node) -> Tuple[Optional[int], Optional[int]]:
        """Traverse tree to locate line and column of first syntax ERROR or MISSING node."""
        if node.type in ("ERROR",) or node.is_missing:
            # tree-sitter uses 0-indexed row and col
            return node.start_point[0] + 1, node.start_point[1] + 1
        for child in node.children:
            if child.has_error:
                found = self._find_first_error_node(child)
                if found[0] is not None:
                    return found
        return None, None
