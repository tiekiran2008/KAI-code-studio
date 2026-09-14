"""
test_fix_suggestion_agent.py
=============================
Unit tests for FixSuggestionAgent implementation and security/validation pipeline.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock

from src.domain.entities.code_review import ReviewFinding, SeverityEnum
from src.domain.entities.fix_suggestion import (
    FixSuggestion,
    FixValidationStatus,
    FixUserDecision,
)
from src.application.agents.fix_suggestion import FixSuggestionAgent
from src.core.errors import LLMQuotaExceededError, WorkflowExecutionError


def _make_finding(
    file_path: str = "src/calculator.py",
    line_number: int = 10,
    issue: str = "Unused variable",
    explanation: str = "Variable 'temp' is defined but never used.",
    suggested_fix: str = "Remove variable 'temp'.",
) -> ReviewFinding:
    return ReviewFinding(
        issue=issue,
        severity=SeverityEnum.MEDIUM,
        explanation=explanation,
        suggested_fix=suggested_fix,
        confidence_score=0.9,
        file_path=file_path,
        line_number=line_number,
    )


class TestFixSuggestionAgent:

    @pytest.mark.asyncio
    async def test_1_valid_finding_generates_valid_fix_suggestion(self):
        """Valid finding with mock LLM returns a complete FixSuggestion."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(
                content='{"proposed_code": "def add(a, b):\\n    return a + b", "explanation": "Add type annotations and clean code", "confidence_score": 0.95}'
            )
        )

        agent = FixSuggestionAgent(llm_provider=mock_llm)

        finding = _make_finding(file_path="src/calc.py", line_number=1)
        original_code = "def add(a, b):\n    temp = 1\n    return a + b"

        fix = await agent.generate_fix(
            finding=finding,
            finding_index=0,
            repository_id="repo_123",
            file_content_override=original_code,
        )

        assert isinstance(fix, FixSuggestion)
        assert fix.finding_index == 0
        assert fix.file_path == "src/calc.py"
        assert fix.original_code == original_code
        assert fix.proposed_code == "def add(a, b):\n    return a + b"
        assert fix.explanation == "Add type annotations and clean code"
        assert fix.confidence_score == 0.95
        assert fix.user_decision == FixUserDecision.PENDING

    @pytest.mark.asyncio
    async def test_2_proposed_code_differs_from_original(self):
        """Proposed code differs from original code."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(
                content='{"proposed_code": "x = 2", "explanation": "Fix constant", "confidence_score": 0.9}'
            )
        )
        agent = FixSuggestionAgent(llm_provider=mock_llm)
        finding = _make_finding(file_path="config.py", line_number=1)

        fix = await agent.generate_fix(
            finding=finding,
            finding_index=0,
            repository_id="repo_123",
            file_content_override="x = 1",
        )
        assert fix.proposed_code != fix.original_code

    @pytest.mark.asyncio
    async def test_3_unified_diff_generated_correctly(self):
        """Diff field contains valid unified git diff labels and hunks."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(
                content='{"proposed_code": "val = 42", "explanation": "Fix val", "confidence_score": 0.9}'
            )
        )
        agent = FixSuggestionAgent(llm_provider=mock_llm)
        finding = _make_finding(file_path="main.py", line_number=1)

        fix = await agent.generate_fix(
            finding=finding,
            finding_index=0,
            repository_id="repo_123",
            file_content_override="val = 10",
        )

        assert "--- a/main.py" in fix.diff
        assert "+++ b/main.py" in fix.diff
        assert "-val = 10" in fix.diff
        assert "+val = 42" in fix.diff

    @pytest.mark.asyncio
    async def test_4_initial_user_decision_is_pending(self):
        """Initial user_decision is always pending."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(
                content='{"proposed_code": "y = 2", "explanation": "Fix", "confidence_score": 0.9}'
            )
        )
        agent = FixSuggestionAgent(llm_provider=mock_llm)
        finding = _make_finding(file_path="test.py", line_number=1)

        fix = await agent.generate_fix(
            finding=finding,
            finding_index=0,
            repository_id="repo_123",
            file_content_override="y = 1",
        )
        assert fix.user_decision == FixUserDecision.PENDING

    @pytest.mark.asyncio
    async def test_5_correct_repository_id_passed_to_rag_filter(self):
        """RAG search receives filter_metadata with exact repository_id."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(
                content='{"proposed_code": "res = True", "explanation": "Fix", "confidence_score": 0.9}'
            )
        )
        mock_retriever = MagicMock()
        mock_retriever.search = AsyncMock(return_value=[
            {"content": "def helper(): return True", "file_path": "utils.py"}
        ])

        agent = FixSuggestionAgent(llm_provider=mock_llm, retriever=mock_retriever)
        finding = _make_finding(file_path="app.py", line_number=1)

        await agent.generate_fix(
            finding=finding,
            finding_index=0,
            repository_id="repo_tenant_a",
            file_content_override="res = False",
        )

        mock_retriever.search.assert_called_once()
        call_kwargs = mock_retriever.search.call_args.kwargs
        assert call_kwargs["filter_metadata"] == {"repo_id": "repo_tenant_a"}

    @pytest.mark.asyncio
    async def test_6_empty_rag_result_uses_source_only(self):
        """If RAG returns empty chunks, generation continues safely using source context."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(
                content='{"proposed_code": "b = 2", "explanation": "Fix b", "confidence_score": 0.88}'
            )
        )
        mock_retriever = MagicMock()
        mock_retriever.search = AsyncMock(return_value=[])

        agent = FixSuggestionAgent(llm_provider=mock_llm, retriever=mock_retriever)
        finding = _make_finding(file_path="b.py", line_number=1)

        fix = await agent.generate_fix(
            finding=finding,
            finding_index=0,
            repository_id="repo_123",
            file_content_override="b = 1",
        )
        assert fix.proposed_code == "b = 2"

    @pytest.mark.asyncio
    async def test_7_cross_repository_rag_data_isolated(self):
        """Retrieval never queries without repository_id filter."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(
                content='{"proposed_code": "c = 3", "explanation": "Fix c", "confidence_score": 0.9}'
            )
        )
        mock_retriever = MagicMock()
        mock_retriever.search = AsyncMock(return_value=[])

        agent = FixSuggestionAgent(llm_provider=mock_llm, retriever=mock_retriever)
        finding = _make_finding()

        await agent.generate_fix(
            finding=finding,
            finding_index=0,
            repository_id="isolated_repo_999",
            file_content_override="c = 1",
        )

        filter_arg = mock_retriever.search.call_args.kwargs.get("filter_metadata")
        assert filter_arg == {"repo_id": "isolated_repo_999"}

    @pytest.mark.asyncio
    async def test_8_malformed_llm_output_raises_workflow_error(self):
        """Non-JSON LLM response raises WorkflowExecutionError."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(content="Here is your fix: just change x to 2")
        )
        agent = FixSuggestionAgent(llm_provider=mock_llm)
        finding = _make_finding()

        with pytest.raises(WorkflowExecutionError):
            await agent.generate_fix(
                finding=finding,
                finding_index=0,
                repository_id="repo_123",
                file_content_override="x = 1",
            )

    @pytest.mark.asyncio
    async def test_9_empty_proposed_code_rejected(self):
        """Empty proposed_code in LLM response raises WorkflowExecutionError."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(
                content='{"proposed_code": "   ", "explanation": "empty", "confidence_score": 0.9}'
            )
        )
        agent = FixSuggestionAgent(llm_provider=mock_llm)
        finding = _make_finding()

        with pytest.raises(WorkflowExecutionError):
            await agent.generate_fix(
                finding=finding,
                finding_index=0,
                repository_id="repo_123",
                file_content_override="x = 1",
            )

    @pytest.mark.asyncio
    async def test_10_identical_proposed_code_rejected(self):
        """Proposed code identical to original snippet raises WorkflowExecutionError."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(
                content='{"proposed_code": "x = 1", "explanation": "No change", "confidence_score": 0.9}'
            )
        )
        agent = FixSuggestionAgent(llm_provider=mock_llm)
        finding = _make_finding()

        with pytest.raises(WorkflowExecutionError):
            await agent.generate_fix(
                finding=finding,
                finding_index=0,
                repository_id="repo_123",
                file_content_override="x = 1",
            )

    @pytest.mark.asyncio
    async def test_11_invalid_confidence_clamped_safely(self):
        """Out of range confidence score in LLM response is clamped or normalized."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(
                content='{"proposed_code": "x = 5", "explanation": "Fix", "confidence_score": 5.0}'
            )
        )
        agent = FixSuggestionAgent(llm_provider=mock_llm)
        finding = _make_finding()

        fix = await agent.generate_fix(
            finding=finding,
            finding_index=0,
            repository_id="repo_123",
            file_content_override="x = 1",
        )
        assert 0.0 <= fix.confidence_score <= 1.0

    @pytest.mark.asyncio
    async def test_12_gemini_429_raises_llm_quota_exceeded(self):
        """429 RESOURCE_EXHAUSTED raises LLMQuotaExceededError without fake fix."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            side_effect=Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for gemini-3.6-flash")
        )
        agent = FixSuggestionAgent(llm_provider=mock_llm)
        finding = _make_finding()

        with pytest.raises(LLMQuotaExceededError):
            await agent.generate_fix(
                finding=finding,
                finding_index=0,
                repository_id="repo_123",
                file_content_override="x = 1",
            )

    @pytest.mark.asyncio
    async def test_13_generic_provider_exception_raises_workflow_error(self):
        """Generic LLM provider error raises WorkflowExecutionError without fake fix."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(side_effect=RuntimeError("API Connection reset"))
        agent = FixSuggestionAgent(llm_provider=mock_llm)
        finding = _make_finding()

        with pytest.raises(WorkflowExecutionError):
            await agent.generate_fix(
                finding=finding,
                finding_index=0,
                repository_id="repo_123",
                file_content_override="x = 1",
            )

    @pytest.mark.asyncio
    async def test_14_missing_file_raises_workflow_error(self):
        """Missing or unreadable file raises WorkflowExecutionError."""
        mock_llm = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.execute = AsyncMock(
            return_value=MagicMock(success=False, error="File not found")
        )

        agent = FixSuggestionAgent(llm_provider=mock_llm, file_adapter=mock_adapter)
        finding = _make_finding(file_path="nonexistent.py")

        with pytest.raises(WorkflowExecutionError):
            await agent.generate_fix(
                finding=finding,
                finding_index=0,
                repository_id="repo_123",
            )

    @pytest.mark.asyncio
    async def test_15_path_traversal_blocked_by_sandbox(self):
        """Path traversal attempt in file_adapter is blocked safely."""
        mock_llm = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.execute = AsyncMock(
            return_value=MagicMock(success=False, error="Path traversal detected")
        )

        agent = FixSuggestionAgent(llm_provider=mock_llm, file_adapter=mock_adapter)
        finding = _make_finding(file_path="../../etc/passwd")

        with pytest.raises(WorkflowExecutionError):
            await agent.generate_fix(
                finding=finding,
                finding_index=0,
                repository_id="repo_123",
            )

    @pytest.mark.asyncio
    async def test_16_python_valid_syntax_validation(self):
        """Valid Python snippet sets validation_status = VALID."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(
                content='{"proposed_code": "def process():\\n    return 42", "explanation": "Fix process", "confidence_score": 0.95}'
            )
        )
        agent = FixSuggestionAgent(llm_provider=mock_llm)
        finding = _make_finding(file_path="service.py")

        fix = await agent.generate_fix(
            finding=finding,
            finding_index=0,
            repository_id="repo_123",
            file_content_override="def process():\n    pass",
        )
        assert fix.validation_status == FixValidationStatus.VALID
        assert "verified" in (fix.validation_message or "")

    @pytest.mark.asyncio
    async def test_17_python_invalid_syntax_validation(self):
        """Invalid Python syntax sets validation_status = INVALID."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(
                content='{"proposed_code": "def broken_func(:\\n return", "explanation": "Broken syntax", "confidence_score": 0.95}'
            )
        )
        agent = FixSuggestionAgent(llm_provider=mock_llm)
        finding = _make_finding(file_path="broken.py")

        fix = await agent.generate_fix(
            finding=finding,
            finding_index=0,
            repository_id="repo_123",
            file_content_override="def broken_func(): pass",
        )
        assert fix.validation_status == FixValidationStatus.INVALID
        assert "syntax error" in (fix.validation_message or "").lower()

    @pytest.mark.asyncio
    async def test_18_unsupported_language_behavior(self):
        """Non-Python files (.ts) set validation_status = PENDING without false syntax claim."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(
                content='{"proposed_code": "const x: number = 42;", "explanation": "TypeScript fix", "confidence_score": 0.95}'
            )
        )
        agent = FixSuggestionAgent(llm_provider=mock_llm)
        finding = _make_finding(file_path="src/index.ts")

        fix = await agent.generate_fix(
            finding=finding,
            finding_index=0,
            repository_id="repo_123",
            file_content_override="const x = 10;",
        )
        assert fix.validation_status == FixValidationStatus.PENDING
        assert fix.language == "ts"
        assert "manual review" in (fix.validation_message or "").lower()

    @pytest.mark.asyncio
    async def test_19_workspace_root_reads_root_file_main_py(self, tmp_path):
        """Root-level files like main.py are correctly read from workspace_root without override."""
        main_py = tmp_path / "main.py"
        main_py.write_text("def hello():\n    print('world')\n    return 42\n", encoding="utf-8")

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(
                content='{"proposed_code": "def hello():\\n    print(\'fixed world\')\\n    return 42\\n", "explanation": "Fix greeting", "confidence_score": 0.95}'
            )
        )
        agent = FixSuggestionAgent(llm_provider=mock_llm)
        finding = _make_finding(file_path="main.py", line_number=2)

        fix = await agent.generate_fix(
            finding=finding,
            finding_index=0,
            repository_id="repo_real_root",
            workspace_root=str(tmp_path),
        )
        assert fix.file_path == "main.py"
        assert "print('world')" in fix.original_code
        assert "print('fixed world')" in fix.proposed_code
        assert "-    print('world')" in fix.diff
        assert "+    print('fixed world')" in fix.diff

    @pytest.mark.asyncio
    async def test_20_workspace_root_reads_nested_file(self, tmp_path):
        """Nested files like src/utils/calc.py are correctly read from workspace_root."""
        nested_dir = tmp_path / "src" / "utils"
        nested_dir.mkdir(parents=True)
        calc_py = nested_dir / "calc.py"
        calc_py.write_text("def multiply(a, b):\n    return a * b\n", encoding="utf-8")

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value=MagicMock(
                content='{"proposed_code": "def multiply(a: int, b: int) -> int:\\n    return a * b\\n", "explanation": "Add types", "confidence_score": 0.95}'
            )
        )
        agent = FixSuggestionAgent(llm_provider=mock_llm)
        finding = _make_finding(file_path="src/utils/calc.py", line_number=1)

        fix = await agent.generate_fix(
            finding=finding,
            finding_index=0,
            repository_id="repo_real_nested",
            workspace_root=str(tmp_path),
        )
        assert fix.file_path == "src/utils/calc.py"
        assert "def multiply(a, b):" in fix.original_code
        assert "def multiply(a: int, b: int)" in fix.proposed_code

    @pytest.mark.asyncio
    async def test_21_no_adapter_and_no_workspace_raises_clear_error(self):
        """When no adapter or workspace_root is available and no override, raises clear WorkflowExecutionError."""
        mock_llm = MagicMock()
        agent = FixSuggestionAgent(llm_provider=mock_llm)
        finding = _make_finding(file_path="main.py", line_number=1)

        with pytest.raises(WorkflowExecutionError, match="No workspace root or file adapter configured"):
            await agent.generate_fix(
                finding=finding,
                finding_index=0,
                repository_id="repo_unconfigured",
            )
