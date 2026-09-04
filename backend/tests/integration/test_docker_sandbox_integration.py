"""
Integration Tests — Docker Sandbox Runtime (Live Environment Check)
===================================================================
Tests live Docker container execution when Docker daemon is available.
If Docker is offline, gracefully skips or verifies BLOCKED_ENVIRONMENT state.
"""
from pathlib import Path
import tempfile
import pytest

from src.domain.entities.sandbox import (
    SandboxExecutionRequest,
    SandboxVerificationStatusEnum,
)
from src.infrastructure.sandbox.runtime import DockerSandboxRuntime
from src.infrastructure.sandbox.sandbox_engine import SandboxExecutionEngine


@pytest.mark.asyncio
async def test_live_docker_sandbox_or_blocked_environment():
    """Verify live Docker sandbox behavior, gracefully handling BLOCKED_ENVIRONMENT if offline."""
    runtime = DockerSandboxRuntime()
    is_available = await runtime.is_available()

    if not is_available:
        # Verify engine returns SANDBOX_UNAVAILABLE without crashing
        engine = SandboxExecutionEngine(runtime=runtime)
        req = SandboxExecutionRequest(
            workspace_root=".",
            language="Python",
            framework="pytest",
        )
        result = await engine.execute_verification(req)
        assert result.status == SandboxVerificationStatusEnum.SANDBOX_UNAVAILABLE
        assert "Docker sandbox container runtime is unavailable" in result.message
        pytest.skip("Docker daemon is not running in test environment (BLOCKED_ENVIRONMENT).")

    # If Docker IS available, run a real isolated container test
    temp_dir = Path(tempfile.mkdtemp(prefix="test_live_docker_"))
    try:
        (temp_dir / "tests").mkdir()
        (temp_dir / "tests" / "test_live.py").write_text("def test_live_pass(): assert 1 + 1 == 2\n")

        engine = SandboxExecutionEngine(runtime=runtime)
        req = SandboxExecutionRequest(
            workspace_root=str(temp_dir),
            language="Python",
            framework="pytest",
            timeout_seconds=30,
        )
        result = await engine.execute_verification(req)
        assert result.status in (SandboxVerificationStatusEnum.PASSED, SandboxVerificationStatusEnum.SANDBOX_UNAVAILABLE)
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
