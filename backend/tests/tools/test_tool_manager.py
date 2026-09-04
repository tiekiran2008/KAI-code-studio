"""
Unit Tests — Tool Manager
=========================
Validates tool manager's timeout handling, retry logic, and permission enforcement.
"""
import pytest
import asyncio
from unittest.mock import MagicMock

from src.domain.models.tools import PermissionLevel, ToolMetadata, ToolResult
from src.domain.interfaces.tools import ITool
from src.infrastructure.tools.registry import ToolRegistry
from src.infrastructure.tools.manager import ToolManager
from src.infrastructure.observability.tool_metrics import ToolMetrics


class MockTool(ITool):
    def __init__(self, name, perms, timeout=1.0, retries=1, success=True, delay=0.0, error=False):
        self.name = name
        self.perms = perms
        self.timeout = timeout
        self.retries = retries
        self.success = success
        self.delay = delay
        self.error = error
        self.execution_count = 0

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self.name,
            description="Mock tool",
            input_schema={},
            output_schema={},
            permissions=self.perms,
            timeout_seconds=self.timeout,
            retry_policy={"max_retries": self.retries, "backoff_factor": 0.1}
        )

    async def execute(self, **kwargs):
        self.execution_count += 1
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        if self.error:
            raise RuntimeError("Tool crashed")
        if self.success:
            return ToolResult(success=True, data="ok")
        return ToolResult(success=False, error="Tool logic failed")


@pytest.fixture
def registry():
    return ToolRegistry()

@pytest.fixture
def manager(registry):
    return ToolManager(registry, ToolMetrics())


@pytest.mark.asyncio
async def test_execute_tool_success(registry, manager):
    tool = MockTool("test_tool", PermissionLevel.READ_ONLY)
    registry.register(tool)
    
    result = await manager.execute_tool("test_tool", {}, PermissionLevel.READ_ONLY, "agent1")
    assert result.success is True
    assert tool.execution_count == 1


@pytest.mark.asyncio
async def test_permission_denied(registry, manager):
    tool = MockTool("secure_tool", PermissionLevel.ADMIN_ONLY)
    registry.register(tool)
    
    result = await manager.execute_tool("secure_tool", {}, PermissionLevel.RESTRICTED, "agent1")
    assert result.success is False
    assert "Permission denied" in result.error
    assert tool.execution_count == 0


@pytest.mark.asyncio
async def test_tool_not_found(manager):
    result = await manager.execute_tool("missing_tool", {}, PermissionLevel.ADMIN_ONLY, "agent1")
    assert result.success is False
    assert "not found in registry" in result.error


@pytest.mark.asyncio
async def test_timeout_enforcement(registry, manager):
    tool = MockTool("slow_tool", PermissionLevel.READ_ONLY, timeout=0.1, delay=0.3, retries=0)
    registry.register(tool)
    
    result = await manager.execute_tool("slow_tool", {}, PermissionLevel.READ_ONLY, "agent1")
    assert result.success is False
    assert "timed out after 0.1" in result.error


@pytest.mark.asyncio
async def test_retry_on_exception(registry, manager):
    tool = MockTool("crashing_tool", PermissionLevel.READ_ONLY, retries=2, error=True)
    registry.register(tool)
    
    result = await manager.execute_tool("crashing_tool", {}, PermissionLevel.READ_ONLY, "agent1")
    assert result.success is False
    assert "Tool execution failed: Tool crashed" in result.error
    assert tool.execution_count == 3  # Initial + 2 retries


def test_build_tool_registry_wires_all_adapters():
    from src.main import _build_tool_registry
    from src.domain.models.tools import PermissionLevel
    from unittest.mock import MagicMock

    mock_qp = MagicMock()
    mock_mem_svc = MagicMock()

    registry = _build_tool_registry(query_processor=mock_qp, memory_service=mock_mem_svc)
    
    # Verify all 5 adapters are registered
    tool_names = [t.name for t in registry.list_tools(min_permission=PermissionLevel.ADMIN_ONLY)]
    assert "github_read" in tool_names
    assert "local_fs_read" in tool_names
    assert "docs_search" in tool_names
    assert "repo_diff" in tool_names
    assert "database_read" in tool_names
    assert len(registry._tools) == 5

    # Verify docs_search adapter has the injected query processor
    docs_tool = registry.get_tool("docs_search")
    assert docs_tool.query_processor is mock_qp

    # Verify database_read adapter has the injected memory service
    db_tool = registry.get_tool("database_read")
    assert db_tool.memory_service is mock_mem_svc


def test_get_tool_manager_dependency_factory():
    from src.interfaces.api.dependencies import get_tool_manager
    from src.domain.models.tools import PermissionLevel
    from unittest.mock import MagicMock

    mock_qp = MagicMock()
    mock_mem_svc = MagicMock()

    manager = get_tool_manager(memory_svc=mock_mem_svc, query_processor=mock_qp)
    registry = manager._registry

    tool_names = [t.name for t in registry.list_tools(min_permission=PermissionLevel.ADMIN_ONLY)]
    assert "github_read" in tool_names
    assert "local_fs_read" in tool_names
    assert "docs_search" in tool_names
    assert "repo_diff" in tool_names
    assert "database_read" in tool_names

    docs_tool = registry.get_tool("docs_search")
    assert docs_tool.query_processor is mock_qp

