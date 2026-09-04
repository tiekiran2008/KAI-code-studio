"""
Tool Metrics
============
Observability layer for tracking tool executions.
"""
from dataclasses import dataclass
from src.core.logger import logger


class ToolMetrics:
    def __init__(self):
        self.executions = 0
        self.failures = 0
        self.total_latency_ms = 0.0

    def record_execution(self, tool_name: str, agent_name: str, success: bool, latency_ms: float, error: str = None) -> None:
        self.executions += 1
        self.total_latency_ms += latency_ms
        if not success:
            self.failures += 1
            logger.error(
                "tool_execution_failed", 
                tool=tool_name, 
                agent=agent_name, 
                error=error, 
                latency_ms=latency_ms
            )
        else:
            logger.info(
                "tool_execution_success", 
                tool=tool_name, 
                agent=agent_name, 
                latency_ms=latency_ms
            )
