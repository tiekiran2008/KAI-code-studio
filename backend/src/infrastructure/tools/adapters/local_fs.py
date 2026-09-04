"""
Local File System Adapter
=========================
Safely reads files, lists directories, and searches within the workspace.
Restricted to a sandbox directory.
"""
import os
import glob
from pathlib import Path
from typing import Any, Dict

from src.domain.interfaces.tools import ITool
from src.domain.models.tools import PermissionLevel, ToolMetadata, ToolResult


class LocalFileSystemAdapter(ITool):
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root).resolve()

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="local_fs_read",
            description="Reads local files, lists directories, or searches files. Restricted to the project workspace.",
            permissions=PermissionLevel.READ_ONLY,
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["read_file", "list_dir", "search"],
                        "description": "Action to perform"
                    },
                    "path": {"type": "string", "description": "Relative path in workspace"},
                    "pattern": {"type": "string", "description": "Glob pattern for search"}
                },
                "required": ["action", "path"]
            },
            output_schema={"type": "object"}
        )

    def _is_safe_path(self, target: Path) -> bool:
        """Prevent path traversal escapes."""
        try:
            target = target.resolve()
            return str(target).startswith(str(self.workspace_root))
        except Exception:
            return False

    async def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action")
        rel_path = kwargs.get("path", "")
        pattern = kwargs.get("pattern", "*")

        target_path = (self.workspace_root / rel_path).resolve()
        
        if not self._is_safe_path(target_path):
            return ToolResult(success=False, error=f"Path traversal detected or out of workspace bound: {rel_path}")

        try:
            if action == "read_file":
                if not target_path.is_file():
                    return ToolResult(success=False, error="File not found or is a directory.")
                content = target_path.read_text(encoding="utf-8", errors="replace")
                return ToolResult(success=True, data={"content": content})
                
            elif action == "list_dir":
                if not target_path.is_dir():
                    return ToolResult(success=False, error="Directory not found or is a file.")
                items = [p.name for p in target_path.iterdir()]
                return ToolResult(success=True, data={"items": items})
                
            elif action == "search":
                if not target_path.is_dir():
                    return ToolResult(success=False, error="Directory not found or is a file.")
                search_glob = str(target_path / pattern)
                matches = glob.glob(search_glob, recursive=True)
                relative_matches = [str(Path(m).relative_to(self.workspace_root)) for m in matches]
                return ToolResult(success=True, data={"matches": relative_matches})
                
            else:
                return ToolResult(success=False, error=f"Invalid action: {action}")
                
        except Exception as e:
            return ToolResult(success=False, error=str(e))
