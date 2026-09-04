"""
Security Audit & Invariant Tests — Tier-2 Container Sandbox
===========================================================
Audits secret isolation, Docker socket protection, static AST constraints,
and container hardening properties.
"""
import ast
import os
from pathlib import Path
import tempfile
import pytest

from src.domain.entities.sandbox import SandboxExecutionRequest
from src.infrastructure.sandbox.runtime import MockSandboxRuntime
from src.infrastructure.sandbox.sandbox_engine import SandboxExecutionEngine


@pytest.fixture
def clean_workspace():
    temp_dir = Path(tempfile.mkdtemp(prefix="test_sec_ws_"))
    (temp_dir / "src").mkdir()
    (temp_dir / "src" / "app.py").write_text("def run(): return True\n")
    (temp_dir / "tests").mkdir()
    (temp_dir / "tests" / "test_app.py").write_text("def test_run(): assert True\n")
    yield temp_dir
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_secret_isolation_backend_env_not_leaked(clean_workspace, monkeypatch):
    """Verify that sensitive host environment variables are NEVER passed to the sandbox container."""
    # Set simulated sensitive backend secrets
    monkeypatch.setenv("GEMINI_API_KEY", "sentinel-gemini-secret-12345")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "sentinel-supabase-secret-67890")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("JWT_SECRET", "super-jwt-secret-abc")

    mock_runtime = MockSandboxRuntime(available=True, mock_exit_code=0)
    engine = SandboxExecutionEngine(runtime=mock_runtime)

    req = SandboxExecutionRequest(
        workspace_root=str(clean_workspace),
        language="Python",
        framework="pytest",
    )

    await engine.execute_verification(req)

    assert mock_runtime.last_spec is not None
    container_env = mock_runtime.last_spec.environment

    # Sensitive keys must be completely ABSENT
    assert "GEMINI_API_KEY" not in container_env
    assert "SUPABASE_SERVICE_ROLE_KEY" not in container_env
    assert "POSTGRES_URL" not in container_env
    assert "JWT_SECRET" not in container_env

    # Only safe static keys exist
    assert container_env.get("PYTHONPATH") == "/workspace"
    assert container_env.get("PYTHONDONTWRITEBYTECODE") == "1"
    assert container_env.get("CI") == "true"


@pytest.mark.asyncio
async def test_no_docker_socket_mounted_in_workload(clean_workspace):
    """Verify that /var/run/docker.sock is NEVER mounted into workload container."""
    mock_runtime = MockSandboxRuntime(available=True, mock_exit_code=0)
    engine = SandboxExecutionEngine(runtime=mock_runtime)

    req = SandboxExecutionRequest(
        workspace_root=str(clean_workspace),
        language="Python",
        framework="pytest",
    )

    await engine.execute_verification(req)

    assert mock_runtime.last_spec is not None
    # Workspace mount must be the ephemeral temp copy only
    assert "docker.sock" not in mock_runtime.last_spec.workspace_mount_path.lower()
    assert mock_runtime.last_spec.container_workspace_path == "/workspace"


@pytest.mark.asyncio
async def test_non_root_and_capabilities_dropped(clean_workspace):
    """Verify that container runs as non-root with all Linux capabilities dropped."""
    mock_runtime = MockSandboxRuntime(available=True, mock_exit_code=0)
    engine = SandboxExecutionEngine(runtime=mock_runtime)

    req = SandboxExecutionRequest(
        workspace_root=str(clean_workspace),
        language="Python",
        framework="pytest",
    )

    await engine.execute_verification(req)

    spec = mock_runtime.last_spec
    assert spec is not None
    assert spec.user == "10001:10001"
    assert spec.cap_drop == ["ALL"]
    assert "no-new-privileges:true" in spec.security_opt
    assert spec.privileged is False
    assert spec.read_only_root is True


def test_static_code_security_audit():
    """AST inspection of sandbox code ensuring no dangerous subprocess, shell=True, or eval calls."""
    sandbox_dir = Path(__file__).resolve().parent.parent.parent / "src" / "infrastructure" / "sandbox"
    assert sandbox_dir.exists() and sandbox_dir.is_dir()

    py_files = list(sandbox_dir.glob("*.py"))
    assert len(py_files) >= 4

    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            # Check for eval() or exec()
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in ("eval", "exec"), f"Forbidden {node.func.id}() call found in {py_file.name}"

            # Check for os.system
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "os" and node.func.attr == "system":
                    pytest.fail(f"Forbidden os.system() found in {py_file.name}")

            # Check for shell=True keyword argument in any call
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        pytest.fail(f"Forbidden shell=True found in {py_file.name}")
