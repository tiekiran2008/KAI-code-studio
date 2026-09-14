"""
Agent API Router
================
FastAPI endpoints for executing the LangGraph multi-agent system.
"""
import structlog
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.application.use_cases.agent_execution import ExecuteAgentWorkflowUseCase
from src.interfaces.api.dependencies import get_agent_use_case, get_auth_service
from src.interfaces.api.v1.schemas.agents import (
    AgentExecuteRequest,
    AgentExecuteResponse,
)
from src.core.errors import LLMQuotaExceededError
from src.core.logger import logger
router = APIRouter()

bearer_scheme = HTTPBearer(auto_error=False)


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    auth_service = Depends(get_auth_service),
) -> Optional[dict]:
    if not credentials:
        return None
    try:
        return auth_service.validate_token(credentials.credentials)
    except Exception:
        return None


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
    user: Optional[dict] = Depends(get_optional_user),
) -> AgentExecuteResponse:
    try:
        user_id = user.get("sub") if user else None
        result = await use_case.execute(
            query=request.query,
            repo_id=request.repo_id,
            session_id=request.session_id,
            user_id=user_id,
        )
        return AgentExecuteResponse(**result)
    except LLMQuotaExceededError as exc:
        logger.warning("agent_execution_quota_exceeded", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI provider rate limit reached. Please retry shortly.",
            headers={"Retry-After": "60"},
        )
    except Exception as exc:
        exc_str = str(exc)
        if any(kw in exc_str for kw in ("429", "RESOURCE_EXHAUSTED", "quota", "rate limit")):
            logger.warning("agent_execution_quota_detected", error=exc_str[:200])
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="AI provider rate limit reached. Please retry shortly.",
                headers={"Retry-After": "60"},
            )
        logger.error("agent_execution_api_error", error=exc_str, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-agent execution error: {exc_str}",
        )

