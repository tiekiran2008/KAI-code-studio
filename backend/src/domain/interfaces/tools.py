"""
Tool Framework Interfaces
=========================
Abstract base classes for the Tool Calling Framework.
Defines contracts for tools, registries, and managers.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.domain.models.tools import PermissionLevel, ToolMetadata, ToolResult


class ITool(ABC):
    """Base interface for all adapter tools."""
    
    @abstractmethod
    def get_metadata(self) -> ToolMetadata:
        """Returns the schema and capability metadata of the tool."""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Executes the tool logic with the provided arguments.
        Must return a standardized ToolResult.
        """
        pass


class IToolRegistry(ABC):
    """Interface for discovering and registering tools."""
    
    @abstractmethod
    def register(self, tool: ITool) -> None:
        """Registers a new tool into the framework."""
        pass

    @abstractmethod
    def get_tool(self, name: str) -> Optional[ITool]:
        """Retrieves a registered tool by its name."""
        pass

    @abstractmethod
    def list_tools(self, min_permission: PermissionLevel = PermissionLevel.READ_ONLY) -> List[ToolMetadata]:
        """
        Returns metadata for all registered tools, filtered by the 
        maximum permission level the caller holds.
        """
        pass


class IToolManager(ABC):
    """
    Interface for orchestrating tool execution. 
    Handles permissions, validation, timeouts, and auditing.
    """
    
    @abstractmethod
    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        caller_permission: PermissionLevel,
        agent_name: str
    ) -> ToolResult:
        """
        Validates permissions and schemas, then executes the tool with
        configured timeout, retries, and full observability logging.
        """
        pass
