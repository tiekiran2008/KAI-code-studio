"""
Database Tool Adapter
=====================
Reads repository metadata, memory records, and analytics from the database.
"""
from typing import Any, Dict

from src.domain.interfaces.tools import ITool
from src.domain.models.tools import PermissionLevel, ToolMetadata, ToolResult
from src.domain.memory.entities import MemorySearchQuery, MemoryType


class DatabaseToolAdapter(ITool):
    def __init__(self, memory_service):
        self.memory_service = memory_service

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="database_read",
            description="Reads repository metadata, conversation history, and user/repo memory records.",
            permissions=PermissionLevel.RESTRICTED,
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["repo_metadata", "conversation_history", "memory_search"],
                        "description": "What data to read"
                    },
                    "user_id": {"type": "string"},
                    "repo_id": {"type": "string"},
                    "session_id": {"type": "string"},
                    "query": {"type": "string", "description": "Search query for memory search"}
                },
                "required": ["action", "user_id"]
            },
            output_schema={"type": "object"}
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action")
        user_id = kwargs.get("user_id")
        repo_id = kwargs.get("repo_id")
        session_id = kwargs.get("session_id")
        query = kwargs.get("query", "")

        try:
            if action == "memory_search":
                if not query:
                    return ToolResult(success=False, error="Query is required for memory search.")
                
                search_query = MemorySearchQuery(
                    query_text=query,
                    user_id=user_id,
                    repository_id=repo_id,
                    top_k=5
                )
                results = await self.memory_service.search(search_query)
                data = [{"id": r.memory.id, "type": r.memory.memory_type.value, "content": r.memory.content} for r in results]
                return ToolResult(success=True, data={"results": data})

            elif action == "conversation_history":
                if not session_id:
                    return ToolResult(success=False, error="Session ID required.")
                
                session_mem = await self.memory_service.get_memory(session_id, user_id)
                if not session_mem or session_mem.memory_type != MemoryType.SHORT_TERM:
                    return ToolResult(success=False, error="Session not found.")
                
                return ToolResult(success=True, data={"history": getattr(session_mem, 'conversation_turns', [])})

            elif action == "repo_metadata":
                # Fallback to Memory Search filtering by REPOSITORY memory type
                search_query = MemorySearchQuery(
                    query_text="repository architecture stack",
                    user_id=user_id,
                    repository_id=repo_id,
                    memory_types=[MemoryType.REPOSITORY],
                    top_k=1
                )
                results = await self.memory_service.search(search_query)
                if results:
                    r = results[0].memory
                    return ToolResult(success=True, data={
                        "summary": r.content,
                        "tech_stack": getattr(r, 'tech_stack', [])
                    })
                return ToolResult(success=False, error="Repo metadata not found.")

            return ToolResult(success=False, error=f"Unknown action: {action}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
