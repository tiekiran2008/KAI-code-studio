"""
Tool Registry
=============
In-memory implementation of IToolRegistry.
Maintains the catalog of registered tool adapters.
"""
from typing import Dict, List, Optional
import threading

from src.domain.interfaces.tools import ITool, IToolRegistry
from src.domain.models.tools import PermissionLevel, ToolMetadata
from src.core.logger import logger


class ToolRegistry(IToolRegistry):
    def __init__(self) -> None:
        self._tools: Dict[str, ITool] = {}
        self._lock = threading.Lock()

    def register(self, tool: ITool) -> None:
        """Register a new tool instance."""
        meta = tool.get_metadata()
        with self._lock:
            if meta.name in self._tools:
                logger.warning("tool_registry_overwrite", tool_name=meta.name)
            self._tools[meta.name] = tool
            logger.info("tool_registered", tool_name=meta.name, permissions=meta.permissions.value)

    def get_tool(self, name: str) -> Optional[ITool]:
        """Fetch a tool by name."""
        with self._lock:
            return self._tools.get(name)

    def list_tools(self, min_permission: PermissionLevel = PermissionLevel.READ_ONLY) -> List[ToolMetadata]:
        """
        List all tools that the caller is authorized to see/use.
        """
        # Permission hierarchy: READ_ONLY (lowest) -> RESTRICTED -> ADMIN_ONLY (highest)
        # Using a simple rank index:
        ranks = {
            PermissionLevel.READ_ONLY: 1,
            PermissionLevel.RESTRICTED: 2,
            PermissionLevel.ADMIN_ONLY: 3,
        }
        
        caller_rank = ranks.get(min_permission, 1)
        
        with self._lock:
            authorized_tools = []
            for t in self._tools.values():
                meta = t.get_metadata()
                tool_rank = ranks.get(meta.permissions, 3) # default secure
                if tool_rank <= caller_rank:
                    authorized_tools.append(meta)
            
            return authorized_tools
