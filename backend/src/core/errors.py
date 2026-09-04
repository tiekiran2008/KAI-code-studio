from fastapi import Request, status
from fastapi.responses import JSONResponse
from .logger import logger

class APIError(Exception):
    """Base class for all API errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ResourceNotFoundError(APIError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class LLMQuotaExceededError(Exception):
    """Raised when the LLM API rejects the request due to quota/rate-limit exhaustion.

    This is NOT a transient error — retrying immediately will not help.
    The review pipeline should mark the review as FAILED and surface this
    information to the caller rather than silently returning empty findings.
    """
    def __init__(self, message: str = "LLM quota exceeded (429 RESOURCE_EXHAUSTED)"):
        super().__init__(message)


class WorkflowExecutionError(Exception):
    """Raised when the agent workflow fails for a non-quota reason.

    Distinct from LLMQuotaExceededError so that callers can differentiate
    between quota exhaustion (potentially retriable later) and hard workflow
    failures (e.g. graph compilation errors, node crashes, parse failures).

    The review pipeline must mark the review as FAILED and must NOT
    generate heuristic/default scores or fake findings when this is raised.
    """
    def __init__(self, message: str = "Agent workflow execution failed"):
        super().__init__(message)

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches all unhandled exceptions."""
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Catches explicitly raised API errors."""
    logger.warning("api_error", message=exc.message, path=request.url.path, status=exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )
