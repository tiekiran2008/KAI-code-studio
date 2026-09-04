"""
Documentation Search Adapter
============================
Integrates with the RAG engine or local filesystem to search docs.
"""
from typing import Any, Dict

from src.domain.interfaces.tools import ITool
from src.domain.models.tools import PermissionLevel, ToolMetadata, ToolResult


class DocumentationSearchAdapter(ITool):
    def __init__(self, query_processor):
        self.query_processor = query_processor

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="docs_search",
            description="Search local, indexed, or API documentation.",
            permissions=PermissionLevel.READ_ONLY,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "doc_type": {
                        "type": "string",
                        "enum": ["local", "indexed", "api"],
                        "description": "Scope of the documentation search"
                    },
                    "repo_id": {"type": "string", "description": "Repository ID for scoped search"}
                },
                "required": ["query", "doc_type", "repo_id"]
            },
            output_schema={"type": "object"}
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query")
        doc_type = kwargs.get("doc_type")
        repo_id = kwargs.get("repo_id")

        if not query or not repo_id:
            return ToolResult(success=False, error="Missing query or repo_id")

        if self.query_processor is None:
            return ToolResult(
                success=False,
                error="Documentation search unavailable: RAG query processor not initialised",
            )

        try:
            # For "indexed" or "api" we route through our RAG Query Processor
            # (Assuming RAG engine can filter by doc types or metadata if implemented)
            result = await self.query_processor.process_query(query, repo_id=repo_id, session_id=None)
            
            return ToolResult(success=True, data={
                "answer": result["answer"],
                "citations": result["citations"]
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))
