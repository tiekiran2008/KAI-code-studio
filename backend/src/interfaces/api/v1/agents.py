"""
Agent API Router
================
FastAPI endpoints for executing the LangGraph multi-agent system.
"""
import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from src.application.use_cases.agent_execution import ExecuteAgentWorkflowUseCase
from src.interfaces.api.dependencies import get_agent_use_case
from src.interfaces.api.v1.schemas.agents import (
    AgentExecuteRequest,
    AgentExecuteResponse,
)
from src.core.logger import logger
router = APIRouter()


@router.post(
    "/execute",
    response_model=AgentExecuteResponse,
    summary="Execute multi-agent software engineering task",
    description=(
        "Submits a request to the LangGraph Supervisor system. The Supervisor delegates "
        "tasks to the Planner, Context, Code Analysis, Bug Detection, Security Review, "
        "Performance, Documentation, Test Generation, and Code Review agents, returning a "
        "validated response with full execution tracing."
    ),
)
async def execute_agents(
    request: AgentExecuteRequest,
    use_case: ExecuteAgentWorkflowUseCase = Depends(get_agent_use_case),
) -> AgentExecuteResponse:
    try:
        result = await use_case.execute(
            query=request.query,
            repo_id=request.repo_id,
            session_id=request.session_id,
        )
        return AgentExecuteResponse(**result)
    except Exception as exc:
        logger.error("agent_execution_api_error", error=str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-agent execution error: {str(exc)}",
        )
