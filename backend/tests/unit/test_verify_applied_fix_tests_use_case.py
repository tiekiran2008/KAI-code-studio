"""
Unit Tests — VerifyAppliedFixTestsUseCase (Tier-2)
==================================================
Verifies eligibility enforcement, source hash consistency, Tier-1 prerequisite,
language detection, sandbox invocation, persistence, and no-host-fallback guarantee.
"""
from pathlib import Path
import hashlib
import tempfile
import pytest
from unittest.mock import MagicMock

from src.core.errors import ResourceNotFoundError, WorkflowExecutionError
from src.domain.entities.sandbox import (
    SandboxVerificationResult,
    SandboxVerificationStatusEnum,
)
from src.domain.entities.verification import VerificationStatus
from src.infrastructure.sandbox.runtime import MockSandboxRuntime
from src.infrastructure.sandbox.sandbox_engine import SandboxExecutionEngine
from src.application.use_cases.verify_applied_fix_tests import VerifyAppliedFixTestsUseCase


# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------

def _make_python_source():
    return b"def add(a, b):\n    return a + b\n"


def _make_fix_dict(workspace: Path, source_bytes: bytes, app_status="applied", static_status="passed", tier2=False):
    source_file = workspace / "src" / "math_utils.py"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(source_bytes)
    h = hashlib.sha256(source_bytes).hexdigest()
    result = {
        "file_path": "src/math_utils.py",
        "application_status": app_status,
        "user_decision": "accepted",
        "new_hash": h,
        "language": "Python",
        "static_verification": {"status": static_status} if static_status else None,
    }
    return result


def _make_review(fix_dict, repo_id="repo-1", status="completed"):
    review = MagicMock()
    review.findings_json = [{"issue": "bug", "fix_suggestion": fix_dict}]
    review.repository_id = repo_id
    review.id = "rev-1"
    review.status = status
    return review



class MockReviewService:
    def __init__(self, review=None, raise_on_update=False):
        self._review = review
        self.raise_on_update = raise_on_update
        self.last_test_result = None

    def get_review(self, review_id, user_id=None):
        return self._review

    def update_finding_test_verification_result(self, review_id, finding_index, verification_result, user_id=None):
        self.last_test_result = verification_result
        if self.raise_on_update:
            raise RuntimeError("persistence failure")
        existing = self._review.findings_json[finding_index]["fix_suggestion"]
        updated = dict(existing)
        if hasattr(verification_result, "model_dump"):
            updated["test_verification"] = verification_result.model_dump(mode="json")
        return updated


class MockRepoService:
    def __init__(self, found=True, detected_lang="Python"):
        self._found = found
        self._lang = detected_lang

    def get_repository(self, user_id, repo_id):
        if not self._found:
            return None

        class MockRepo:
            detected_stack = {"language": self._lang}

        return MockRepo()


def _make_engine(available=True, exit_code=0, stdout="1 passed in 0.1s", stderr="", timeout=False):
    runtime = MockSandboxRuntime(
        available=available,
        mock_exit_code=exit_code,
        mock_stdout=stdout,
        mock_stderr=stderr,
        simulate_timeout=timeout,
    )
    return SandboxExecutionEngine(runtime=runtime)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_use_case_passes_on_happy_path():
    """Full happy-path: applied, Tier-1 passed, hash match → PASSED."""
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        src = _make_python_source()
        fix = _make_fix_dict(workspace, src)
        review = _make_review(fix)
        engine = _make_engine(available=True, exit_code=0, stdout=".\n1 passed in 0.05s")
        use_case = VerifyAppliedFixTestsUseCase(
            review_service=MockReviewService(review),
            repository_service=MockRepoService(),
            sandbox_engine=engine,
            workspace_root_resolver=lambda u, r: tmp,
        )

        result = await use_case.execute("rev-1", 0, "user-1")
        assert result["verification"].status == SandboxVerificationStatusEnum.PASSED
        assert result["verification"].tests_passed == 1
        assert "1 passed in 0.05s" in result["verification"].stdout_summary


@pytest.mark.asyncio
async def test_use_case_fails_on_review_not_found():
    """Raises ResourceNotFoundError when review is missing."""
    use_case = VerifyAppliedFixTestsUseCase(
        review_service=MockReviewService(review=None),
        repository_service=MockRepoService(),
    )
    with pytest.raises(ResourceNotFoundError, match="Review not found"):
        await use_case.execute("rev-1", 0, "user-1")


@pytest.mark.asyncio
async def test_use_case_fails_on_negative_index():
    use_case = VerifyAppliedFixTestsUseCase(
        review_service=MockReviewService(review=None),
        repository_service=MockRepoService(),
    )
    with pytest.raises(WorkflowExecutionError, match="finding_index must be >= 0"):
        await use_case.execute("rev-1", -1, "user-1")


@pytest.mark.asyncio
async def test_use_case_fails_on_repo_not_found():
    with tempfile.TemporaryDirectory() as tmp:
        src = _make_python_source()
        fix = _make_fix_dict(Path(tmp), src)
        review = _make_review(fix)
        use_case = VerifyAppliedFixTestsUseCase(
            review_service=MockReviewService(review),
            repository_service=MockRepoService(found=False),
        )
        with pytest.raises(ResourceNotFoundError, match="Repository not found"):
            await use_case.execute("rev-1", 0, "user-1")


@pytest.mark.asyncio
async def test_use_case_rejects_not_applied_fix():
    with tempfile.TemporaryDirectory() as tmp:
        src = _make_python_source()
        fix = _make_fix_dict(Path(tmp), src, app_status="not_applied")
        review = _make_review(fix)
        use_case = VerifyAppliedFixTestsUseCase(
            review_service=MockReviewService(review),
            repository_service=MockRepoService(),
            workspace_root_resolver=lambda u, r: tmp,
        )
        with pytest.raises(WorkflowExecutionError, match="must be applied"):
            await use_case.execute("rev-1", 0, "user-1")


@pytest.mark.asyncio
async def test_use_case_enforces_tier1_prerequisite():
    """Tier-2 must be rejected when Tier-1 has not passed."""
    with tempfile.TemporaryDirectory() as tmp:
        src = _make_python_source()
        fix = _make_fix_dict(Path(tmp), src, static_status="failed")
        review = _make_review(fix)
        use_case = VerifyAppliedFixTestsUseCase(
            review_service=MockReviewService(review),
            repository_service=MockRepoService(),
            workspace_root_resolver=lambda u, r: tmp,
        )
        with pytest.raises(WorkflowExecutionError, match="static verification must"):
            await use_case.execute("rev-1", 0, "user-1")


@pytest.mark.asyncio
async def test_use_case_source_changed_detection():
    """Detects file modification after apply and raises WorkflowExecutionError."""
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        src = _make_python_source()
        fix = _make_fix_dict(workspace, src)
        # Corrupt the file on disk so hash no longer matches stored new_hash
        (workspace / "src" / "math_utils.py").write_text("modified content!\n")
        review = _make_review(fix)
        engine = _make_engine()
        use_case = VerifyAppliedFixTestsUseCase(
            review_service=MockReviewService(review),
            repository_service=MockRepoService(),
            sandbox_engine=engine,
            workspace_root_resolver=lambda u, r: tmp,
        )
        with pytest.raises(WorkflowExecutionError, match="Source file was modified"):
            await use_case.execute("rev-1", 0, "user-1")


@pytest.mark.asyncio
async def test_use_case_unsupported_language_does_not_execute():
    """Non-Python/non-pytest repository returns UNSUPPORTED without running container."""
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        src = b"const x = 1;\n"
        fix = _make_fix_dict(workspace, src)
        fix["file_path"] = "src/index.ts"
        # Update the hash for the .ts source
        (workspace / "src" / "index.ts").write_bytes(src)
        fix["new_hash"] = hashlib.sha256(src).hexdigest()
        review = _make_review(fix)
        runtime = MockSandboxRuntime(available=True)
        engine = SandboxExecutionEngine(runtime=runtime)
        use_case = VerifyAppliedFixTestsUseCase(
            review_service=MockReviewService(review),
            repository_service=MockRepoService(detected_lang="JavaScript/TypeScript"),
            sandbox_engine=engine,
            workspace_root_resolver=lambda u, r: tmp,
        )
        result = await use_case.execute("rev-1", 0, "user-1")
        # No container should run for unsupported language
        assert result["verification"].status == SandboxVerificationStatusEnum.UNSUPPORTED
        assert runtime.execution_count == 0


@pytest.mark.asyncio
async def test_use_case_sandbox_unavailable_no_host_fallback():
    """When Docker is unavailable, returns SANDBOX_UNAVAILABLE — zero host execution."""
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        src = _make_python_source()
        fix = _make_fix_dict(workspace, src)
        review = _make_review(fix)
        runtime = MockSandboxRuntime(available=False)
        engine = SandboxExecutionEngine(runtime=runtime)
        use_case = VerifyAppliedFixTestsUseCase(
            review_service=MockReviewService(review),
            repository_service=MockRepoService(),
            sandbox_engine=engine,
            workspace_root_resolver=lambda u, r: tmp,
        )
        result = await use_case.execute("rev-1", 0, "user-1")
        assert result["verification"].status == SandboxVerificationStatusEnum.SANDBOX_UNAVAILABLE
        assert runtime.execution_count == 0


@pytest.mark.asyncio
async def test_use_case_persists_result():
    """Verifies that result is persisted into review via update_finding_test_verification_result."""
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        src = _make_python_source()
        fix = _make_fix_dict(workspace, src)
        review = _make_review(fix)
        svc = MockReviewService(review)
        engine = _make_engine(available=True, exit_code=0, stdout="2 passed in 0.08s")
        use_case = VerifyAppliedFixTestsUseCase(
            review_service=svc,
            repository_service=MockRepoService(),
            sandbox_engine=engine,
            workspace_root_resolver=lambda u, r: tmp,
        )
        await use_case.execute("rev-1", 0, "user-1")
        assert svc.last_test_result is not None
        assert svc.last_test_result.status == SandboxVerificationStatusEnum.PASSED


@pytest.mark.asyncio
async def test_use_case_timed_out():
    """Timeout produces TIMED_OUT result, not a false PASS."""
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        src = _make_python_source()
        fix = _make_fix_dict(workspace, src)
        review = _make_review(fix)
        engine = _make_engine(available=True, timeout=True)
        use_case = VerifyAppliedFixTestsUseCase(
            review_service=MockReviewService(review),
            repository_service=MockRepoService(),
            sandbox_engine=engine,
            workspace_root_resolver=lambda u, r: tmp,
        )
        result = await use_case.execute("rev-1", 0, "user-1")
        assert result["verification"].status == SandboxVerificationStatusEnum.TIMED_OUT
        assert result["verification"].timed_out is True
