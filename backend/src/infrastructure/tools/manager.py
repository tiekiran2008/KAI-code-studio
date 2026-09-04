"""
Tool Manager
============
Orchestrates tool execution, applying permissions, timeouts, retries,
and capturing observability metrics.
"""
import time
import asyncio
from typing import Any, Dict

from src.domain.interfaces.tools import IToolRegistry, IToolManager
from src.domain.models.tools import PermissionLevel, ToolResult
from src.infrastructure.observability.tool_metrics import ToolMetrics
from src.core.logger import logger


class ToolExecutionError(Exception):
    pass


class ToolManager(IToolManager):
    def __init__(self, registry: IToolRegistry, metrics: ToolMetrics = None):
        self._registry = registry
        self._metrics = metrics or ToolMetrics()

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        caller_permission: PermissionLevel,
        agent_name: str
    ) -> ToolResult:
        """
        Execute a tool safely with timeouts, retries, and permission checks.
        """
        tool = self._registry.get_tool(tool_name)
        if not tool:
            err = f"Tool '{tool_name}' not found in registry."
            self._metrics.record_execution(tool_name, agent_name, False, 0.0, err)
            return ToolResult(success=False, error=err)

        meta = tool.get_metadata()

        # 1. Permission check
        if not self._check_permission(caller_permission, meta.permissions):
            err = f"Permission denied. Agent '{agent_name}' ({caller_permission}) cannot execute tool '{tool_name}' ({meta.permissions})."
            self._metrics.record_execution(tool_name, agent_name, False, 0.0, err)
            return ToolResult(success=False, error=err)

        # 2. Execution with Retries & Timeout
        max_retries = meta.retry_policy.get("max_retries", 1)
        backoff = meta.retry_policy.get("backoff_factor", 2.0)
        timeout = meta.timeout_seconds

        attempt = 0
        last_error = None
        start_time = time.perf_counter()

        while attempt <= max_retries:
            try:
                logger.debug("tool_execution_attempt", tool=tool_name, attempt=attempt+1)
                
                # Enforce timeout via asyncio
                result = await asyncio.wait_for(
                    tool.execute(**arguments),
                    timeout=timeout
                )
                
                latency = (time.perf_counter() - start_time) * 1000
                result.latency_ms = latency
                
                self._metrics.record_execution(tool_name, agent_name, result.success, latency, result.error)
                return result

            except asyncio.TimeoutError:
                last_error = f"Tool execution timed out after {timeout} seconds."
            except Exception as e:
                last_error = f"Tool execution failed: {str(e)}"

            attempt += 1
            if attempt <= max_retries:
                await asyncio.sleep(backoff ** attempt)

        # Failure after retries
        latency = (time.perf_counter() - start_time) * 1000
        self._metrics.record_execution(tool_name, agent_name, False, latency, last_error)
        return ToolResult(success=False, error=last_error, latency_ms=latency)

    def _check_permission(self, caller_level: PermissionLevel, required_level: PermissionLevel) -> bool:
        ranks = {
            PermissionLevel.READ_ONLY: 1,
            PermissionLevel.RESTRICTED: 2,
            PermissionLevel.ADMIN_ONLY: 3,
        }
        return ranks.get(caller_level, 1) >= ranks.get(required_level, 3)
