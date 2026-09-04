"""
Execute Agent Workflow Use Case
===============================
Top-level application use case that invokes the compiled LangGraph multi-agent graph,
manages error boundaries, measures execution metrics, and logs the agent trajectory.

Phase 7 additions
-----------------
- Injects MemoryService for pre-execution context enrichment.
- Persists episodic memory after every successful agent session.
- Initialises short-term session memory at the start of each call.
"""
import time
from typing import Any, Dict, Optional

from src.application.agents.graph import build_agent_graph
from src.domain.interfaces.llm import ILLMProvider
from src.application.rag.query_processor import QueryProcessor
from src.core.config import settings
from src.core.logger import logger
from src.core.errors import LLMQuotaExceededError, WorkflowExecutionError


class ExecuteAgentWorkflowUseCase:
    def __init__(
        self,
        llm_provider: ILLMProvider,
        query_processor: QueryProcessor,
        memory_service=None,  # Optional[MemoryService]
        tool_manager=None,    # Optional[ToolManager]
    ) -> None:
        self.graph = build_agent_graph(llm_provider, query_processor, tool_manager)
        self._memory = memory_service
        self._tool_manager = tool_manager

    async def execute(
        self,
        query: str,
        repo_id: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        review_config: Optional[Dict[str, Any]] = None,
        on_progress: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Runs the multi-agent graph to process the user request.

        Memory flow
        -----------
        1. Init/refresh short-term session memory.
        2. Enrich retrieved_context with relevant long-term / episodic memories.
        3. Execute the LangGraph graph with enriched state.
        4. Persist an episodic memory record for this session.
        """
        start_time = time.perf_counter()
        effective_user = user_id or "anonymous"
        logger.info(
            "agent_workflow_execution_start",
            repo_id=repo_id,
            query=query[:80],
            user_id=effective_user,
        )

        # ---- Phase 7: Memory pre-enrichment ----
        memory_context = ""
        if self._memory is not None and effective_user != "anonymous":
            try:
                await self._memory.init_session(
                    user_id=effective_user,
                    session_id=session_id or "default",
                    query=query,
                    repository_id=repo_id,
                )
                memory_context = await self._memory.enrich_agent_context(
                    query=query,
                    user_id=effective_user,
                    session_id=session_id,
                    repository_id=repo_id,
                    existing_rag_context="",
                    token_budget=settings.MEMORY_CONTEXT_TOKEN_BUDGET,
                )
            except Exception as exc:
                logger.warning("memory_pre_enrichment_failed", error=str(exc))

        initial_state = {
            "query": query,
            "repo_id": repo_id,
            "session_id": session_id,
            "review_config": review_config or {},
            "plan": None,
            "pending_tasks": [],
            "completed_tasks": [],
            "retrieved_context": memory_context,  # Pre-seeded with memory context
            "retrieved_chunks": [],
            "tool_calls": [],
            "tool_results": [],
            "agent_outputs": {},
            "citations": [],
            "confidence_score": 0.0,
            "groundedness_ratio": 0.0,
            "is_eval_passed": False,
            "evaluation_notes": "",
            "retry_count": 0,
            "next_agent": "supervisor",
            "sender": "user",
            "final_answer": "",
            "execution_trace": [],
            "errors": [],
        }

        try:
            config = {"recursion_limit": settings.AGENT_MAX_RECURSION_LIMIT}

            if callable(on_progress):
                await on_progress("planning", 20, "Planner agent analyzing review tasks…")
                final_state = dict(initial_state)
                try:
                    async for event in self.graph.astream(initial_state, config=config):
                        if isinstance(event, dict):
                            for node_name, node_state in event.items():
                                if isinstance(node_state, dict):
                                    final_state.update(node_state)
                                if node_name == "planner":
                                    await on_progress("planning", 20, "Planner agent created execution plan…")
                                elif node_name == "context":
                                    await on_progress("retrieving_context", 35, "Retrieving repository code context…")
                                elif node_name in ("code_review", "security_review", "performance", "bug_detection"):
                                    await on_progress("reviewing", 50, f"Running AI code review ({node_name})…")
                                elif node_name in ("code_quality", "refactoring_analysis", "report_generation", "evaluation"):
                                    await on_progress("evaluating", 75, f"Evaluating findings ({node_name})…")
                except Exception:
                    # Fallback to ainvoke if astream is unsupported in mock
                    final_state = await self.graph.ainvoke(initial_state, config=config)
            else:
                final_state = await self.graph.ainvoke(initial_state, config=config)

            total_latency = round((time.perf_counter() - start_time) * 1000, 2)


            logger.info(
                "agent_workflow_execution_complete",
                total_latency_ms=total_latency,
                confidence=final_state.get("confidence_score", 0.0),
                num_outputs=len(final_state.get("agent_outputs", {})),
            )

            # ---- Phase 7: Persist episodic memory ----
            if self._memory is not None and effective_user != "anonymous":
                try:
                    await self._memory.save_episode(
                        user_id=effective_user,
                        session_id=session_id or "default",
                        query=query,
                        repository_id=repo_id,
                        agent_outputs=final_state.get("agent_outputs", {}),
                        final_answer=final_state.get("final_answer", ""),
                        confidence_score=final_state.get("confidence_score", 0.0),
                        citations=final_state.get("citations", []),
                        execution_trace=final_state.get("execution_trace", []),
                    )
                except Exception as exc:
                    logger.warning("episodic_memory_save_failed", error=str(exc))

            return {
                "answer": final_state.get("final_answer", "No answer generated."),
                "plan": final_state.get("plan", {}),
                "agent_outputs": final_state.get("agent_outputs", {}),
                "citations": final_state.get("citations", []),
                "confidence_score": final_state.get("confidence_score", 0.0),
                "groundedness_ratio": final_state.get("groundedness_ratio", 0.0),
                "execution_trace": final_state.get("execution_trace", []),
                "latency_ms": total_latency,
                "session_id": session_id or "agent_session",
                "repo_id": repo_id,
            }

        except LLMQuotaExceededError:
            # Already a typed quota error — re-raise as-is so callers handle it correctly.
            total_latency = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error("agent_workflow_quota_exceeded_passthrough", latency_ms=total_latency)
            raise

        except Exception as exc:
            total_latency = round((time.perf_counter() - start_time) * 1000, 2)
            # Sanitize: truncate to 300 chars to avoid leaking secrets or PII in logs.
            sanitized_error = str(exc)[:300]

            # Detect Gemini 429 / quota-exceeded — wrap and re-raise so
            # callers can mark the review as FAILED instead of completed.
            if any(
                s in sanitized_error
                for s in ("429", "RESOURCE_EXHAUSTED", "quota", "Quota", "rate limit")
            ):
                logger.error(
                    "agent_workflow_quota_exceeded",
                    error=sanitized_error,
                    latency_ms=total_latency,
                )
                raise LLMQuotaExceededError(sanitized_error) from exc

            # All other unexpected failures → wrap in WorkflowExecutionError so callers
            # receive a typed, non-quota exception and can mark the review FAILED.
            # Never swallow the error; never return empty outputs that masquerade as success.
            logger.error(
                "agent_workflow_execution_failed",
                error=sanitized_error,
                latency_ms=total_latency,
            )
            raise WorkflowExecutionError(sanitized_error) from exc

