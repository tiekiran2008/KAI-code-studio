"""
Sandbox Runtime Abstraction
===========================
Abstract interface and concrete runtime implementations for ephemeral container sandboxes.
"""
from abc import ABC, abstractmethod
import asyncio
import time
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from src.core.logger import logger


class ContainerRunSpec(BaseModel):
    """Hardened execution specification for an ephemeral container."""
    image: str = Field(default="python:3.11-slim", description="Predefined trusted image name")
    command: List[str] = Field(..., description="Immutable command argv array")
    workspace_mount_path: str = Field(..., description="Host path to the ephemeral workspace copy")
    container_workspace_path: str = Field(default="/workspace", description="Target container workspace directory")
    environment: Dict[str, str] = Field(default_factory=dict, description="Strict allowlisted environment variables")
    memory_limit: str = Field(default="512m", description="Hard memory ceiling (no swap)")
    cpu_quota: int = Field(default=100000, description="CPU CFS quota (100000 = 1.0 CPU)")
    cpu_period: int = Field(default=100000, description="CPU CFS period")
    pids_limit: int = Field(default=64, description="Maximum number of simultaneous processes/threads")
    network_disabled: bool = Field(default=True, description="Enforce --network none")
    read_only_root: bool = Field(default=True, description="Mount root filesystem read-only")
    user: str = Field(default="10001:10001", description="Non-root user and group ID")
    cap_drop: List[str] = Field(default_factory=lambda: ["ALL"], description="Linux capabilities to drop")
    security_opt: List[str] = Field(default_factory=lambda: ["no-new-privileges:true"], description="Security options")
    privileged: bool = Field(default=False, description="Privileged container mode is strictly forbidden")
    tmpfs: Dict[str, str] = Field(
        default_factory=lambda: {"/tmp": "rw,noexec,nosuid,size=64m"},
        description="Isolated tmpfs mounts",
    )
    timeout_seconds: int = Field(default=30, ge=5, le=60, description="Hard execution timeout in seconds")


class ContainerRunResult(BaseModel):
    """Raw result captured from container execution."""
    exit_code: int = Field(..., description="Process exit code")
    stdout: str = Field(default="", description="Captured standard output")
    stderr: str = Field(default="", description="Captured standard error")
    duration_ms: int = Field(default=0, ge=0, description="Execution duration in milliseconds")
    timed_out: bool = Field(default=False, description="True if container was killed due to timeout")
    resource_limit_hit: bool = Field(default=False, description="True if memory or PID limits were triggered")


class ISandboxRuntime(ABC):
    """Abstract interface for sandbox container engines."""

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if container engine / daemon is reachable and functioning."""
        raise NotImplementedError

    @abstractmethod
    async def run_container(self, spec: ContainerRunSpec) -> ContainerRunResult:
        """Execute container according to spec, returning bounded result and enforcing cleanup."""
        raise NotImplementedError


class DockerSandboxRuntime(ISandboxRuntime):
    """Production Docker SDK sandbox runtime."""

    def __init__(self) -> None:
        self._client = None
        self._initialized = False

    def _get_client(self):
        if not self._initialized:
            self._initialized = True
            try:
                import docker
                self._client = docker.from_env()
            except Exception as exc:
                logger.warning(f"Docker client initialization failed: {exc}")
                self._client = None
        return self._client

    async def is_available(self) -> bool:
        """Ping Docker daemon to verify availability."""
        def _ping() -> bool:
            client = self._get_client()
            if not client:
                return False
            try:
                return bool(client.ping())
            except Exception:
                return False

        return await asyncio.to_thread(_ping)

    async def run_container(self, spec: ContainerRunSpec) -> ContainerRunResult:
        """Execute container via Docker SDK in a worker thread with async timeout."""
        client = self._get_client()
        if not client:
            raise RuntimeError("Docker daemon is not available")

        start_time = time.time()
        container = None

        def _create_and_run():
            nonlocal container
            volumes = {
                spec.workspace_mount_path: {
                    "bind": spec.container_workspace_path,
                    "mode": "rw",
                }
            }

            container = client.containers.create(
                image=spec.image,
                command=spec.command,
                network_mode="none" if spec.network_disabled else "bridge",
                volumes=volumes,
                working_dir=spec.container_workspace_path,
                environment=spec.environment,
                mem_limit=spec.memory_limit,
                memswap_limit=spec.memory_limit,
                cpu_quota=spec.cpu_quota,
                cpu_period=spec.cpu_period,
                pids_limit=spec.pids_limit,
                cap_drop=spec.cap_drop,
                security_opt=spec.security_opt,
                user=spec.user,
                read_only=spec.read_only_root,
                tmpfs=spec.tmpfs,
                privileged=False,
                detach=True,
            )

            container.start()
            status_res = container.wait(timeout=spec.timeout_seconds)
            exit_code = status_res.get("StatusCode", 1) if isinstance(status_res, dict) else int(status_res)
            logs = container.logs(stdout=True, stderr=True)
            stdout_str = logs.decode("utf-8", errors="replace") if isinstance(logs, bytes) else str(logs)
            return exit_code, stdout_str, ""

        try:
            exit_code, stdout_str, stderr_str = await asyncio.wait_for(
                asyncio.to_thread(_create_and_run),
                timeout=spec.timeout_seconds + 5,
            )
            duration_ms = int((time.time() - start_time) * 1000)
            return ContainerRunResult(
                exit_code=exit_code,
                stdout=stdout_str,
                stderr=stderr_str,
                duration_ms=duration_ms,
                timed_out=False,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Container execution timed out after {spec.timeout_seconds}s")
            duration_ms = int((time.time() - start_time) * 1000)
            if container:
                try:
                    await asyncio.to_thread(container.kill)
                except Exception as kill_err:
                    logger.warning(f"Error killing timed out container: {kill_err}")
            return ContainerRunResult(
                exit_code=-1,
                stdout="",
                stderr="Execution timed out.",
                duration_ms=duration_ms,
                timed_out=True,
            )
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            return ContainerRunResult(
                exit_code=1,
                stdout="",
                stderr=f"Container execution failed: {exc}",
                duration_ms=duration_ms,
                timed_out=False,
            )
        finally:
            if container:
                try:
                    await asyncio.to_thread(container.remove, force=True)
                except Exception as rem_err:
                    logger.warning(f"Error removing container: {rem_err}")


class MockSandboxRuntime(ISandboxRuntime):
    """Deterministic mock runtime for automated security and unit tests."""

    def __init__(
        self,
        available: bool = True,
        mock_exit_code: int = 0,
        mock_stdout: str = "",
        mock_stderr: str = "",
        mock_duration_ms: int = 15,
        simulate_timeout: bool = False,
        simulate_resource_limit: bool = False,
        simulate_exception: Optional[Exception] = None,
    ) -> None:
        self.available = available
        self.mock_exit_code = mock_exit_code
        self.mock_stdout = mock_stdout
        self.mock_stderr = mock_stderr
        self.mock_duration_ms = mock_duration_ms
        self.simulate_timeout = simulate_timeout
        self.simulate_resource_limit = simulate_resource_limit
        self.simulate_exception = simulate_exception
        self.last_spec: Optional[ContainerRunSpec] = None
        self.execution_count: int = 0

    async def is_available(self) -> bool:
        return self.available

    async def run_container(self, spec: ContainerRunSpec) -> ContainerRunResult:
        self.last_spec = spec
        self.execution_count += 1

        if self.simulate_exception:
            raise self.simulate_exception

        if self.simulate_timeout:
            return ContainerRunResult(
                exit_code=-1,
                stdout="",
                stderr="Execution timed out.",
                duration_ms=spec.timeout_seconds * 1000,
                timed_out=True,
                resource_limit_hit=False,
            )

        if self.simulate_resource_limit:
            return ContainerRunResult(
                exit_code=137,  # SIGKILL (OOM or PID limit)
                stdout=self.mock_stdout,
                stderr="Container killed by OOM killer or PID limit.",
                duration_ms=self.mock_duration_ms,
                timed_out=False,
                resource_limit_hit=True,
            )

        return ContainerRunResult(
            exit_code=self.mock_exit_code,
            stdout=self.mock_stdout,
            stderr=self.mock_stderr,
            duration_ms=self.mock_duration_ms,
            timed_out=False,
            resource_limit_hit=False,
        )
