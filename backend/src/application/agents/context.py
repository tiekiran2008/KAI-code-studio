"""
Context Agent
=============
Interacts with the Phase 5 RAG Engine to retrieve repository code,
documentation, line numbers, and symbol context for the graph.
"""
import time
from typing import Dict, Any, Optional
from src.application.rag.query_processor import QueryProcessor
from src.domain.models.agents import AgentState, AgentType, AgentOutput
from src.core.logger import logger


class ContextAgent:
    def __init__(self, query_processor: QueryProcessor) -> None:
        self.processor = query_processor

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        start = time.perf_counter()
        query = state.get("query", "")
        repo_id = state.get("repo_id", "")
        session_id = state.get("session_id")

        logger.info("context_agent_execution_start", repo_id=repo_id, query=query[:60])

        rag_response = await self.processor.process(
            question=query,
            repo_id=repo_id,
            session_id=session_id,
        )

        # Convert citations to dictionaries
        citations_list = [
            {
                "file_path": c.file_path,
                "repo_path": c.repo_path,
                "class_name": c.class_name,
                "function_name": c.function_name,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "symbol_type": c.symbol_type,
                "confidence": c.confidence,
                "chunk_id": c.chunk_id,
            }
            for c in rag_response.citations
        ]

        # Extract structured text context from citations and answer
        context_text = f"Initial RAG Summary:\n{rag_response.answer}\n\n"
        if rag_response.metadata and "context_tokens" in rag_response.metadata:
            context_text += f"Retrieved Chunk Count: {rag_response.retrieved_chunk_count}\n"

        latency = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "context_agent_execution_complete",
            retrieved_chunks=rag_response.retrieved_chunk_count,
            citations=len(citations_list),
            latency_ms=latency,
        )

        output_data = {
            "summary": f"Retrieved {rag_response.retrieved_chunk_count} code chunks and {len(citations_list)} citations.",
            "details": rag_response.answer,
            "data": {
                "chunk_count": rag_response.retrieved_chunk_count,
                "confidence": rag_response.confidence,
                "intent": rag_response.intent.value,
            },
        }

        # Update completed tasks
        pending = [t for t in state.get("pending_tasks", []) if t != AgentType.CONTEXT.value]
        completed = state.get("completed_tasks", []) + [AgentType.CONTEXT.value]

        return {
            "retrieved_context": context_text,
            "citations": citations_list,
            "agent_outputs": {AgentType.CONTEXT.value: output_data},
            "pending_tasks": pending,
            "completed_tasks": completed,
            "sender": AgentType.CONTEXT.value,
            "execution_trace": [{
                "agent": AgentType.CONTEXT.value,
                "action": "retrieved_repository_knowledge",
                "chunks_count": rag_response.retrieved_chunk_count,
                "latency_ms": latency,
            }],
        }
