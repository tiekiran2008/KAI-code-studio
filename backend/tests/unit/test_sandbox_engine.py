"""
Unit Tests — Sandbox Execution Engine
=====================================
Verifies end-to-end sandbox lifecycle, timeout enforcement, exit code handling,
Docker unavailable handling with ZERO host fallback, and concurrency limits.
"""
from pathlib import Path
import tempfile
import pytest

from src.domain.entities.sandbox import (
    SandboxExecutionRequest,
    SandboxVerificationStatusEnum,
)
from src.infrastructure.sandbox.runtime import MockSandboxRuntime
from src.infrastructure.sandbox.sandbox_engine import SandboxExecutionEngine


@pytest.fixture
def sample_workspace():
    temp_dir = Path(tempfile.mkdtemp(prefix="test_engine_ws_"))
    (temp_dir / "src").mkdir()
    (temp_dir / "src" / "math_utils.py").write_text("def multiply(a, b): return a * b\n")
    (temp_dir / "tests").mkdir()
    (temp_dir / "tests" / "test_math.py").write_text("def test_multiply(): assert 2 * 3 == 6\n")
    yield temp_dir
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_sandbox_engine_passing_pytest(sample_workspace):
    mock_runtime = MockSandboxRuntime(
        available=True,
        mock_exit_code=0,
        mock_stdout=".\n1 passed in 0.05s\n",
        mock_stderr="",
        mock_duration_ms=45,
    )
    engine = SandboxExecutionEngine(runtime=mock_runtime)

    req = SandboxExecutionRequest(
        workspace_root=str(sample_workspace),
        language="Python",
        framework="pytest",
        timeout_seconds=30,
        relative_target_path="tests/test_math.py",
    )

    result = await engine.execute_verification(req)

    assert result.status == SandboxVerificationStatusEnum.PASSED
    assert result.exit_code == 0
    assert result.tests_total == 1
    assert result.tests_passed == 1
    assert result.tests_failed == 0
    assert result.timed_out is False
    assert result.resource_limit_hit is False
    assert "1 passed in 0.05s" in result.stdout_summary
    assert mock_runtime.execution_count == 1

    # Verify hardened container run spec
    assert mock_runtime.last_spec is not None
    assert mock_runtime.last_spec.network_disabled is True
    assert mock_runtime.last_spec.cap_drop == ["ALL"]
    assert mock_runtime.last_spec.user == "10001:10001"
    assert mock_runtime.last_spec.read_only_root is True
    assert mock_runtime.last_spec.privileged is False
    assert mock_runtime.last_spec.pids_limit == 64
    assert mock_runtime.last_spec.memory_limit == "512m"


@pytest.mark.asyncio
async def test_sandbox_engine_failing_pytest(sample_workspace):
    mock_runtime = MockSandboxRuntime(
        available=True,
        mock_exit_code=1,
        mock_stdout="F\n1 failed in 0.08s\n",
        mock_stderr="AssertionError: 2 * 3 != 99\n",
        mock_duration_ms=60,
    )
    engine = SandboxExecutionEngine(runtime=mock_runtime)

    req = SandboxExecutionRequest(
        workspace_root=str(sample_workspace),
        language="Python",
        framework="pytest",
    )

    result = await engine.execute_verification(req)

    assert result.status == SandboxVerificationStatusEnum.FAILED
    assert result.exit_code == 1
    assert result.tests_total == 1
    assert result.tests_passed == 0
    assert result.tests_failed == 1
    assert result.timed_out is False


@pytest.mark.asyncio
async def test_sandbox_engine_timeout(sample_workspace):
    mock_runtime = MockSandboxRuntime(
        available=True,
        simulate_timeout=True,
    )
    engine = SandboxExecutionEngine(runtime=mock_runtime)

    req = SandboxExecutionRequest(
        workspace_root=str(sample_workspace),
        language="Python",
        framework="pytest",
        timeout_seconds=10,
    )

    result = await engine.execute_verification(req)

    assert result.status == SandboxVerificationStatusEnum.TIMED_OUT
    assert result.timed_out is True
    assert "timed out" in result.message.lower()


@pytest.mark.asyncio
async def test_sandbox_engine_resource_limit_hit(sample_workspace):
    mock_runtime = MockSandboxRuntime(
        available=True,
        simulate_resource_limit=True,
    )
    engine = SandboxExecutionEngine(runtime=mock_runtime)

    req = SandboxExecutionRequest(
        workspace_root=str(sample_workspace),
        language="Python",
        framework="pytest",
    )

    result = await engine.execute_verification(req)

    assert result.status == SandboxVerificationStatusEnum.FAILED
    assert result.resource_limit_hit is True
    assert result.exit_code == 137
    assert "resource limit" in result.message.lower()


@pytest.mark.asyncio
async def test_sandbox_engine_docker_unavailable_returns_safe_state(sample_workspace):
    """When Docker daemon is offline, engine returns SANDBOX_UNAVAILABLE with ZERO host fallback."""
    mock_runtime = MockSandboxRuntime(
        available=False,
    )
    engine = SandboxExecutionEngine(runtime=mock_runtime)

    req = SandboxExecutionRequest(
        workspace_root=str(sample_workspace),
        language="Python",
        framework="pytest",
    )

    result = await engine.execute_verification(req)

    assert result.status == SandboxVerificationStatusEnum.SANDBOX_UNAVAILABLE
    assert result.exit_code is None
    assert mock_runtime.execution_count == 0
    assert "Docker sandbox container runtime is unavailable" in result.message


@pytest.mark.asyncio
async def test_sandbox_engine_unsupported_language():
    engine = SandboxExecutionEngine(runtime=MockSandboxRuntime())

    req = SandboxExecutionRequest(
        workspace_root="/dummy/path",
        language="JavaScript",
        framework="vitest",
    )

    result = await engine.execute_verification(req)

    assert result.status == SandboxVerificationStatusEnum.UNSUPPORTED
    assert "Only Python + pytest is supported" in result.message
