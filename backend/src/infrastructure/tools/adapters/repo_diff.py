"""
Repository Diff Adapter
=======================
Compares commits, branches, detects changed files, and generates summaries.
Uses safe, read-only git commands restricted to the workspace.
"""
import subprocess
from pathlib import Path
from typing import Any, Dict

from src.domain.interfaces.tools import ITool
from src.domain.models.tools import PermissionLevel, ToolMetadata, ToolResult
from src.core.logger import logger


class RepositoryDiffAdapter(ITool):
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root).resolve()

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="repo_diff",
            description="Compares commits, branches, detects changed files, and generates summaries.",
            permissions=PermissionLevel.READ_ONLY,
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["compare_commits", "changed_files", "summary"],
                        "description": "Diff action to perform"
                    },
                    "base": {"type": "string", "description": "Base commit/branch"},
                    "head": {"type": "string", "description": "Head commit/branch"}
                },
                "required": ["action", "base", "head"]
            },
            output_schema={"type": "object"}
        )

    def _run_git(self, args: list) -> str:
        cmd = ["git"] + args
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.workspace_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=15.0
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error("git_command_failed", cmd=" ".join(cmd), error=e.stderr)
            raise RuntimeError(f"Git error: {e.stderr.strip()}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Git command timed out")

    async def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action")
        base = kwargs.get("base", "")
        head = kwargs.get("head", "")

        # Simple sanitization to prevent command injection
        if not base.isalnum() and not all(c in "-_./~^:" for c in base):
            return ToolResult(success=False, error="Invalid base ref characters")
        if not head.isalnum() and not all(c in "-_./~^:" for c in head):
            return ToolResult(success=False, error="Invalid head ref characters")

        try:
            if action == "compare_commits":
                diff = self._run_git(["diff", f"{base}...{head}"])
                return ToolResult(success=True, data={"diff": diff[:10000]}) # Truncate massive diffs
                
            elif action == "changed_files":
                files = self._run_git(["diff", "--name-only", f"{base}...{head}"])
                return ToolResult(success=True, data={"files": files.splitlines()})
                
            elif action == "summary":
                stat = self._run_git(["diff", "--stat", f"{base}...{head}"])
                return ToolResult(success=True, data={"summary": stat})
                
            else:
                return ToolResult(success=False, error=f"Invalid action: {action}")
                
        except Exception as e:
            return ToolResult(success=False, error=str(e))
