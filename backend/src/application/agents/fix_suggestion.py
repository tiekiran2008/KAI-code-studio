"""
Fix Suggestion Agent
====================
AI Agent that generates targeted, line-accurate code fix suggestions for a
single review finding using source code context and repository-isolated RAG.

IMPORTANT: This agent NEVER modifies repository files on disk.
           It ONLY generates in-memory FixSuggestion objects.
"""
import ast
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.domain.entities.code_review import ReviewFinding
from src.domain.entities.fix_suggestion import (
    FixSuggestion,
    FixValidationStatus,
    FixUserDecision,
)
from src.domain.interfaces.llm import ILLMProvider
from src.infrastructure.tools.adapters.local_fs import LocalFileSystemAdapter
from src.application.rag.hybrid_retriever import HybridRetriever
from src.application.utils.diff_generator import generate_unified_diff
from src.core.errors import LLMQuotaExceededError, WorkflowExecutionError
from src.core.logger import logger

_SYSTEM_PROMPT = """You are a Principal Software Engineer and Code Repair Specialist.
Your task is to generate a precise, minimal code fix for a single specified code review finding.

CRITICAL INSTRUCTIONS:
1. Fix ONLY the specified issue in the provided source code snippet.
2. Make the smallest reasonable change required to resolve the finding.
3. Do NOT modify unrelated logic, refactor surrounding code, or alter code style.
4. Preserve exact indentation and scope.
5. THIS IS A SUGGESTION ONLY — you are NOT modifying the repository directly.

You MUST return ONLY a raw JSON object with this exact structure:
{
  "proposed_code": "exact updated code snippet",
  "explanation": "clear, concise rationale explaining what was changed and why",
  "confidence_score": 0.95
}

Rules for output:
- Do NOT wrap JSON in markdown code blocks (no ```json).
- proposed_code MUST be a non-empty string containing the complete updated snippet.
- proposed_code MUST differ from the original code snippet.
- confidence_score must be a float between 0.0 and 1.0.
"""

_QUOTA_STRINGS = ("429", "RESOURCE_EXHAUSTED", "quota", "Quota", "rate limit")


class FixSuggestionAgent:
    """Agent responsible for generating automated fix suggestions for review findings."""

    def __init__(
        self,
        llm_provider: ILLMProvider,
        file_adapter: Optional[LocalFileSystemAdapter] = None,
        retriever: Optional[HybridRetriever] = None,
    ) -> None:
        self.llm = llm_provider
        self.file_adapter = file_adapter
        self.retriever = retriever

    def extract_source_window(
        self,
        file_content: str,
        line_number: Optional[int],
        window_size: int = 20,
    ) -> str:
        """Extract a bounded line window around line_number from file content."""
        if not file_content:
            return ""

        lines = file_content.splitlines()
        if not lines:
            return ""

        if line_number is None or line_number <= 0:
            # If no valid line number, return first 50 lines bounded
            return "\n".join(lines[:50])

        target_idx = line_number - 1  # 1-indexed to 0-indexed
        start_idx = max(0, target_idx - window_size)
        end_idx = min(len(lines), target_idx + window_size + 1)

        return "\n".join(lines[start_idx:end_idx])

    async def _retrieve_rag_context(
        self,
        finding: ReviewFinding,
        repository_id: str,
    ) -> str:
        """Retrieve relevant repository context strictly isolated by repository_id."""
        if not self.retriever or not repository_id:
            return ""

        query_text = f"{finding.issue} {finding.explanation} {finding.suggested_fix or ''}"
        try:
            chunks = await self.retriever.search(
                query=query_text,
                filter_metadata={"repo_id": repository_id},
                limit=3,
            )
            if not chunks:
                return ""

            formatted_context = []
            for idx, chunk in enumerate(chunks, 1):
                content = chunk.get("content", "").strip()
                file_path = chunk.get("file_path", "")
                if content:
                    formatted_context.append(f"--- Context Chunk {idx} ({file_path}) ---\n{content}")

            return "\n\n".join(formatted_context)
        except Exception as exc:
            logger.warning(
                "fix_suggestion_rag_retrieval_failed",
                repo_id=repository_id,
                error=str(exc),
            )
            return ""

    def validate_syntax(self, code_snippet: str, file_path: str) -> tuple[FixValidationStatus, Optional[str]]:
        """Perform static in-memory syntax validation where practical."""
        ext = Path(file_path).suffix.lower() if file_path else ""

        if ext == ".py":
            # Attempt 1: Parse directly
            try:
                ast.parse(code_snippet)
                return FixValidationStatus.VALID, "Python syntax verified"
            except SyntaxError as e1:
                # Attempt 2: Try wrapping in dummy function for indented function body snippets
                try:
                    indented_code = "def _wrapper():\n" + "\n".join(
                        f"    {line}" for line in code_snippet.splitlines()
                    )
                    ast.parse(indented_code)
                    return FixValidationStatus.VALID, "Python snippet syntax verified (within function scope)"
                except SyntaxError:
                    return FixValidationStatus.INVALID, f"Python syntax error: {e1.msg} at line {e1.lineno}"

        # For unsupported languages (.js, .ts, .java, etc.), mark PENDING to avoid false claims
        return FixValidationStatus.PENDING, f"Syntax validation not natively supported for {ext or 'this language'}; manual review recommended"

    async def generate_fix(
        self,
        finding: ReviewFinding,
        finding_index: int,
        repository_id: str,
        workspace_root: Optional[str] = None,
        file_content_override: Optional[str] = None,
    ) -> FixSuggestion:
        """Generate a validated FixSuggestion for a single review finding.

        Parameters
        ----------
        finding : ReviewFinding
            The review finding requiring a fix.
        finding_index : int
            Array index of finding in parent review.
        repository_id : str
            Repository identifier for strict tenant/RAG isolation.
        workspace_root : Optional[str]
            Root path of workspace for file reading.
        file_content_override : Optional[str]
            Direct file content string (bypasses file_adapter reading if provided).

        Returns
        -------
        FixSuggestion
            Strongly typed in-memory fix suggestion.
        """
        if finding_index < 0:
            raise WorkflowExecutionError("finding_index must be >= 0")

        file_path = finding.file_path or ""
        if not file_path and not file_content_override:
            raise WorkflowExecutionError("Finding missing file_path for fix generation")

        # 1. Fetch Source Code Context (READ-ONLY)
        original_file_content = ""
        if file_content_override is not None:
            original_file_content = file_content_override
        elif self.file_adapter:
            res = await self.file_adapter.execute(action="read_file", path=file_path)
            if not res.success:
                raise WorkflowExecutionError(f"Failed to read file '{file_path}': {res.error}")
            original_file_content = res.data.get("content", "")
        elif workspace_root:
            adapter = LocalFileSystemAdapter(workspace_root=workspace_root)
            res = await adapter.execute(action="read_file", path=file_path)
            if not res.success:
                raise WorkflowExecutionError(f"Failed to read file '{file_path}': {res.error}")
            original_file_content = res.data.get("content", "")

        original_snippet = self.extract_source_window(
            file_content=original_file_content,
            line_number=finding.line_number,
            window_size=20,
        )

        if not original_snippet or not original_snippet.strip():
            raise WorkflowExecutionError(f"Source context empty for file '{file_path}'")

        # 2. Retrieve Repository-Isolated RAG Context
        rag_context = await self._retrieve_rag_context(finding, repository_id)

        # 3. Construct Prompt
        user_prompt = f"""Target File: {file_path}
Line Number: {finding.line_number or 'N/A'}

[CODE REVIEW FINDING]
Issue: {finding.issue}
Severity: {finding.severity.value if hasattr(finding.severity, 'value') else finding.severity}
Explanation: {finding.explanation}
Suggested Fix Concept: {finding.suggested_fix or 'None provided'}

[ORIGINAL CODE SNIPPET]
{original_snippet}
"""
        if rag_context:
            user_prompt += f"\n[RELEVANT REPOSITORY CONTEXT]\n{rag_context}\n"

        user_prompt += "\nPlease generate the JSON fix suggestion containing 'proposed_code', 'explanation', and 'confidence_score'."

        # 4. Invoke LLM with Quota & Failure Safeguards
        try:
            llm_res = await self.llm.complete(
                prompt=user_prompt,
                system=_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=2048,
            )
            response_text = llm_res.content or ""
        except Exception as exc:
            err_msg = str(exc)
            if any(qs in err_msg for qs in _QUOTA_STRINGS):
                logger.error("fix_suggestion_llm_quota_exceeded", error=err_msg)
                raise LLMQuotaExceededError(f"LLM quota exceeded during fix generation: {err_msg}")
            logger.error("fix_suggestion_llm_failed", error=err_msg)
            raise WorkflowExecutionError(f"LLM provider failed during fix generation: {err_msg}")

        # Check raw response string for 429 quota indicators
        if any(qs in response_text for qs in _QUOTA_STRINGS) and ("429" in response_text or "RESOURCE_EXHAUSTED" in response_text):
            raise LLMQuotaExceededError("LLM quota exceeded (429 RESOURCE_EXHAUSTED)")

        # 5. Parse Structured Output
        cleaned_json = response_text.strip()
        if cleaned_json.startswith("```"):
            cleaned_json = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned_json)
            cleaned_json = re.sub(r"\n?```$", "", cleaned_json).strip()

        try:
            parsed = json.loads(cleaned_json)
        except Exception as parse_err:
            logger.error("fix_suggestion_json_parse_failed", response=response_text[:300])
            raise WorkflowExecutionError(f"Failed to parse structured LLM fix response: {parse_err}")

        proposed_code = parsed.get("proposed_code", "")
        explanation = parsed.get("explanation", "")
        confidence_score = parsed.get("confidence_score", 0.9)

        # 6. Validate Output Requirements
        if not proposed_code or not proposed_code.strip():
            raise WorkflowExecutionError("LLM returned empty proposed code")

        if proposed_code.strip() == original_snippet.strip():
            raise WorkflowExecutionError("Proposed code is identical to original code snippet")

        if not explanation or not explanation.strip():
            explanation = f"Automated fix for: {finding.issue}"

        try:
            confidence_score = float(confidence_score)
            confidence_score = max(0.0, min(1.0, confidence_score))
        except (ValueError, TypeError):
            confidence_score = 0.85

        # 7. Language-Aware Syntax Validation
        val_status, val_msg = self.validate_syntax(proposed_code, file_path)

        # 8. Deterministic Unified Diff Generation
        diff = generate_unified_diff(
            original_code=original_snippet,
            proposed_code=proposed_code,
            file_path=file_path,
        )

        language_meta = Path(file_path).suffix.lstrip(".").lower() if file_path else None

        # 9. Return Typed FixSuggestion (User Decision defaults to PENDING)
        return FixSuggestion(
            finding_index=finding_index,
            file_path=file_path,
            original_code=original_snippet,
            proposed_code=proposed_code,
            explanation=explanation,
            diff=diff,
            confidence_score=confidence_score,
            validation_status=val_status,
            user_decision=FixUserDecision.PENDING,
            language=language_meta,
            validation_message=val_msg,
        )
