"""
Sandbox Execution Engine
========================
High-level orchestrator for Tier-2 isolated container verification.
Enforces scope validation, bounded concurrency, copy-on-execution, strict resource/network limits,
and complete cleanup with ZERO host fallback.
"""
import asyncio
from datetime import datetime, timezone
import time
from typing import Optional

from src.core.logger import logger
from src.domain.entities.sandbox import (
    SandboxExecutionRequest,
    SandboxVerificationResult,
    SandboxVerificationStatusEnum,
)
from src.infrastructure.sandbox.runtime import (
    ISandboxRuntime,
    DockerSandboxRuntime,
    ContainerRunSpec,
)
from src.infrastructure.sandbox.ephemeral_workspace import EphemeralWorkspaceManager
from src.infrastructure.sandbox.pytest_runner import PytestSandboxRunner

# Maximum simultaneous sandbox jobs on host
MAX_CONCURRENT_SANDBOX_JOBS = 2


class SandboxExecutionEngine:
    """Coordinates isolated Tier-2 container verification."""

    def __init__(
        self,
        runtime: Optional[ISandboxRuntime] = None,
        workspace_manager: Optional[EphemeralWorkspaceManager] = None,
        pytest_runner: Optional[PytestSandboxRunner] = None,
    ) -> None:
        self.runtime = runtime or DockerSandboxRuntime()
        self.workspace_manager = workspace_manager or EphemeralWorkspaceManager()
        self.pytest_runner = pytest_runner or PytestSandboxRunner()
        self._concurrency_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SANDBOX_JOBS)

    async def execute_verification(
        self,
        request: SandboxExecutionRequest,
    ) -> SandboxVerificationResult:
        """Execute Tier-2 verification for an applied fix in an ephemeral sandbox.

        Parameters
        ----------
        request : SandboxExecutionRequest
            Structured execution parameters.

        Returns
        -------
        SandboxVerificationResult
            Structured verification result.
        """
        start_time = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Scope Enforcement: Python + pytest only
        lang = (request.language or "").strip().lower()
        framework = (request.framework or "").strip().lower()

        if lang != "python" or framework != "pytest":
            return SandboxVerificationResult(
                status=SandboxVerificationStatusEnum.UNSUPPORTED,
                verification_type=request.verification_type,
                test_framework=request.framework,
                command_label=f"{request.framework} (unsupported)",
                exit_code=None,
                duration_ms=0,
                message=f"Tier-2 verification does not support language '{request.language}' with framework '{request.framework}'. Only Python + pytest is supported.",
                verified_at=now_iso,
            )

        # 2. Concurrency limiting
        async with self._concurrency_semaphore:
            # 3. Check sandbox runtime availability
            try:
                is_avail = await self.runtime.is_available()
            except Exception as avail_err:
                logger.warning(f"Error checking sandbox availability: {avail_err}")
                is_avail = False

            if not is_avail:
                return SandboxVerificationResult(
                    status=SandboxVerificationStatusEnum.SANDBOX_UNAVAILABLE,
                    verification_type=request.verification_type,
                    test_framework=request.framework,
                    command_label="pytest -q",
                    exit_code=None,
                    duration_ms=int((time.time() - start_time) * 1000),
                    message="Docker sandbox container runtime is unavailable. Test execution was not run.",
                    error_details="Docker daemon is offline or not installed. Host execution is strictly forbidden.",
                    verified_at=now_iso,
                )

            # 4. Generate allowlisted command
            try:
                command = self.pytest_runner.build_command(request.relative_target_path)
            except Exception as cmd_err:
                return SandboxVerificationResult(
                    status=SandboxVerificationStatusEnum.EXECUTION_ERROR,
                    verification_type=request.verification_type,
                    test_framework=request.framework,
                    command_label="pytest -q",
                    exit_code=None,
                    duration_ms=int((time.time() - start_time) * 1000),
                    message=f"Failed to generate allowlisted command: {cmd_err}",
                    error_details=str(cmd_err),
                    verified_at=now_iso,
                )

            # 5. Create ephemeral copy-on-execution workspace
            try:
                ws_context = self.workspace_manager.create_snapshot(request.workspace_root)
            except Exception as ws_err:
                return SandboxVerificationResult(
                    status=SandboxVerificationStatusEnum.EXECUTION_ERROR,
                    verification_type=request.verification_type,
                    test_framework=request.framework,
                    command_label="pytest -q",
                    exit_code=None,
                    duration_ms=int((time.time() - start_time) * 1000),
                    message=f"Failed to create ephemeral workspace: {ws_err}",
                    error_details=str(ws_err),
                    verified_at=now_iso,
                )

            # 6. Execute container inside ephemeral workspace with guaranteed cleanup
            try:
                # Safe, allowlisted environment: ZERO host secrets
                clean_env = {
                    "PYTHONPATH": "/workspace",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONUNBUFFERED": "1",
                    "CI": "true",
                }

                spec = ContainerRunSpec(
                    image="python:3.11-slim",
                    command=command,
                    workspace_mount_path=str(ws_context.temp_path),
                    container_workspace_path="/workspace",
                    environment=clean_env,
                    memory_limit="512m",
                    cpu_quota=100000,
                    cpu_period=100000,
                    pids_limit=64,
                    network_disabled=True,
                    read_only_root=True,
                    user="10001:10001",
                    cap_drop=["ALL"],
                    security_opt=["no-new-privileges:true"],
                    privileged=False,
                    tmpfs={"/tmp": "rw,noexec,nosuid,size=64m"},
                    timeout_seconds=min(max(request.timeout_seconds, 5), 60),
                )

                raw_result = await self.runtime.run_container(spec)

                duration_ms = raw_result.duration_ms or int((time.time() - start_time) * 1000)
                bounded_stdout = self.pytest_runner.bound_output(raw_result.stdout)
                bounded_stderr = self.pytest_runner.bound_output(raw_result.stderr)
                total, passed, failed, skipped = self.pytest_runner.parse_pytest_summary(bounded_stdout)

                if raw_result.timed_out:
                    return SandboxVerificationResult(
                        status=SandboxVerificationStatusEnum.TIMED_OUT,
                        verification_type=request.verification_type,
                        test_framework=request.framework,
                        command_label="pytest -q",
                        exit_code=raw_result.exit_code,
                        duration_ms=duration_ms,
                        tests_total=total,
                        tests_passed=passed,
                        tests_failed=failed,
                        tests_skipped=skipped,
                        stdout_summary=bounded_stdout,
                        stderr_summary=bounded_stderr,
                        timed_out=True,
                        resource_limit_hit=False,
                        message=f"Pytest execution timed out after {spec.timeout_seconds}s and was terminated.",
                        verified_at=now_iso,
                    )

                if raw_result.resource_limit_hit:
                    return SandboxVerificationResult(
                        status=SandboxVerificationStatusEnum.FAILED,
                        verification_type=request.verification_type,
                        test_framework=request.framework,
                        command_label="pytest -q",
                        exit_code=raw_result.exit_code,
                        duration_ms=duration_ms,
                        tests_total=total,
                        tests_passed=passed,
                        tests_failed=failed,
                        tests_skipped=skipped,
                        stdout_summary=bounded_stdout,
                        stderr_summary=bounded_stderr,
                        timed_out=False,
                        resource_limit_hit=True,
                        message="Container exceeded resource limits (OOM or process limit).",
                        verified_at=now_iso,
                    )

                if raw_result.exit_code == 0:
                    status = SandboxVerificationStatusEnum.PASSED
                    msg = "All isolated repository tests passed successfully."
                else:
                    status = SandboxVerificationStatusEnum.FAILED
                    msg = f"Isolated repository tests failed with exit code {raw_result.exit_code}."

                return SandboxVerificationResult(
                    status=status,
                    verification_type=request.verification_type,
                    test_framework=request.framework,
                    command_label="pytest -q",
                    exit_code=raw_result.exit_code,
                    duration_ms=duration_ms,
                    tests_total=total,
                    tests_passed=passed,
                    tests_failed=failed,
                    tests_skipped=skipped,
                    stdout_summary=bounded_stdout,
                    stderr_summary=bounded_stderr,
                    timed_out=False,
                    resource_limit_hit=False,
                    message=msg,
                    verified_at=now_iso,
                )

            except Exception as exec_err:
                logger.error(f"Unexpected error in sandbox execution: {exec_err}")
                return SandboxVerificationResult(
                    status=SandboxVerificationStatusEnum.EXECUTION_ERROR,
                    verification_type=request.verification_type,
                    test_framework=request.framework,
                    command_label="pytest -q",
                    exit_code=None,
                    duration_ms=int((time.time() - start_time) * 1000),
                    message=f"Sandbox execution error: {exec_err}",
                    error_details=str(exec_err),
                    verified_at=now_iso,
                )

            finally:
                # Guaranteed cleanup of temporary workspace
                ws_context.cleanup()
