"""
Software Engineering AI Agent — Application Entry Point
=======================================================
Bootstrap module for the FastAPI application.

Startup sequence (each step is non-fatal — failures are logged and the server
continues so that partial degradation is observable via /api/v1/health):

  1. Structured logging initialisation
  2. PostgreSQL  — DDL auto-provision via SQLAlchemy ``create_all``
  3. Redis       — connectivity ping
  4. Qdrant      — connectivity probe (``get_collections``)
  5. MemoryManager singleton — wired to PG + Qdrant + Redis
  6. ToolRegistry — all adapters registered
  7. LangGraph graph — compiled once (warm-up) and cached on ``app.state``

Run with:
    uvicorn src.main:app --reload          (development)
    uvicorn src.main:app --host 0.0.0.0   (production)
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import redis as redis_lib
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import settings, mask_url_credentials
from src.core.errors import (
    APIError,
    LLMQuotaExceededError,
    api_error_handler,
    global_exception_handler,
    llm_quota_exception_handler,
)
from src.core.logger import logger, setup_logging
from src.interfaces.api.v1.router import api_router
from src.interfaces.api.dependencies import (
    _get_embedding_service,
    _get_vector_db,
    _get_llm_provider,
)


# ---------------------------------------------------------------------------
# Middleware helpers
# ---------------------------------------------------------------------------

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects a unique ``X-Request-ID`` header into every request/response."""

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """Injects ``X-Process-Time-Ms`` into every response."""

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
        return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

from fastapi.encoders import jsonable_encoder


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Returns 422 with structured validation error detail."""
    err_detail = jsonable_encoder(exc.errors())
    logger.warning(
        "validation_error",
        path=request.url.path,
        errors=err_detail,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": err_detail},
    )



async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Wraps FastAPI's built-in HTTPException into a consistent JSON envelope."""
    logger.warning(
        "http_exception",
        path=request.url.path,
        status_code=exc.status_code,
        detail=exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# ---------------------------------------------------------------------------
# Startup / shutdown helpers
# ---------------------------------------------------------------------------

def _init_postgres() -> None:
    """Auto-provision all SQLAlchemy-declared tables, sync schema drift, and repair legacy data (idempotent)."""
    from sqlalchemy import create_engine
    from src.infrastructure.persistence.models import Base  # noqa: F401 — side-effect import registers all models
    from src.infrastructure.persistence.schema_migrator import sync_schema

    engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
    try:
        added_columns = sync_schema(engine)
        if added_columns:
            logger.info("postgres_schema_synced", added_columns=added_columns)
    except Exception as exc:
        logger.warning("postgres_schema_sync_warning", error=str(exc))
    finally:
        engine.dispose()
    logger.info("postgres_init_ok", message="All database tables verified / synchronized")


def _init_redis() -> None:
    """Ping Redis to verify connectivity."""
    client = redis_lib.from_url(settings.REDIS_URL, **settings.get_redis_kwargs())
    client.ping()
    client.close()
    logger.info("redis_init_ok", url=mask_url_credentials(settings.REDIS_URL))


def _init_qdrant() -> None:
    """Probe Qdrant to verify connectivity."""
    from qdrant_client import QdrantClient

    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None, timeout=5)
    client.get_collections()
    logger.info("qdrant_init_ok", url=mask_url_credentials(settings.QDRANT_URL))


def _build_memory_manager() -> Any:
    """
    Instantiate the full MemoryManager singleton.

    Returns the ``MemoryManager`` instance, or ``None`` if any dependency is
    unavailable (graceful degradation).
    """
    import redis as redis_lib_inner

    from src.infrastructure.embeddings.sentence_transformer_service import (
        SentenceTransformerService,
    )
    from src.infrastructure.memory.memory_encryptor import FernetMemoryEncryptor
    from src.infrastructure.memory.memory_manager import MemoryManager
    from src.infrastructure.memory.postgres_memory_repository import (
        PostgresMemoryRepository,
    )
    from src.infrastructure.memory.qdrant_memory_vector_store import (
        QdrantMemoryVectorStore,
    )
    from src.infrastructure.memory.redis_session_cache import RedisSessionCache
    from src.infrastructure.observability.memory_metrics import MemoryMetrics
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = session_factory()

    encryptor = FernetMemoryEncryptor(settings.MEMORY_ENCRYPTION_KEY or None)
    repo = PostgresMemoryRepository(db_session, encryptor)

    vector_store = QdrantMemoryVectorStore(
        qdrant_url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
        vector_dim=settings.MEMORY_VECTOR_DIM,
        collection_name=settings.MEMORY_VECTOR_COLLECTION,
    )

    redis_client = redis_lib_inner.from_url(settings.REDIS_URL, **settings.get_redis_kwargs())
    session_cache = RedisSessionCache(redis_client)

    embedding_service = _get_embedding_service()

    manager = MemoryManager(
        repository=repo,
        vector_store=vector_store,
        session_cache=session_cache,
        embedding_service=embedding_service,
        metrics=MemoryMetrics(),
        short_term_ttl=settings.MEMORY_SHORT_TERM_TTL_SECONDS,
        long_term_ttl_days=settings.MEMORY_LONG_TERM_TTL_DAYS,
    )

    logger.info("memory_manager_init_ok", collection=settings.MEMORY_VECTOR_COLLECTION)
    return manager


def _build_tool_registry(query_processor: Any = None, memory_service: Any = None) -> Any:
    """
    Instantiate and populate the ToolRegistry singleton with all standard adapters.

    Returns the ``ToolRegistry`` instance.
    """
    from src.infrastructure.tools.registry import ToolRegistry
    from src.infrastructure.tools.adapters.github import GitHubToolAdapter
    from src.infrastructure.tools.adapters.local_fs import LocalFileSystemAdapter
    from src.infrastructure.tools.adapters.docs import DocumentationSearchAdapter
    from src.infrastructure.tools.adapters.database import DatabaseToolAdapter
    from src.infrastructure.tools.adapters.repo_diff import RepositoryDiffAdapter

    registry = ToolRegistry()
    workspace_root = settings.WORKSPACE_ROOT

    # GitHubToolAdapter is registered without a static token at startup.
    # Per-user OAuth token injection is handled through the request-scoped
    # dependency layer (get_tool_manager / get_user_scoped_github_token).
    # Public GitHub repos work without a token; private repos require OAuth connection.
    registry.register(GitHubToolAdapter())
    registry.register(LocalFileSystemAdapter(workspace_root=workspace_root))
    registry.register(DocumentationSearchAdapter(query_processor=query_processor))
    registry.register(RepositoryDiffAdapter(workspace_root=workspace_root))
    if memory_service is not None:
        registry.register(DatabaseToolAdapter(memory_service=memory_service))

    logger.info(
        "tool_registry_init_ok",
        registered_tools=len(registry._tools),
        workspace=workspace_root,
    )
    return registry


def _build_langgraph_supervisor(app_state: Any) -> Any:
    """
    Warm-compile the LangGraph StateGraph so the first real request pays no
    compilation cost. Stores the compiled graph on ``app.state.agent_graph``
    and populates ``app.state.tool_registry``.
    """
    import redis as redis_lib_inner
    from src.application.rag.query_processor import QueryProcessor
    from src.application.services.memory_service import MemoryService
    from src.application.agents.graph import build_agent_graph
    from src.infrastructure.tools.manager import ToolManager
    from src.infrastructure.observability.tool_metrics import ToolMetrics

    llm_provider = _get_llm_provider()
    embedding_service = _get_embedding_service()
    vector_db = _get_vector_db()
    redis_client = redis_lib_inner.from_url(settings.REDIS_URL, **settings.get_redis_kwargs())

    query_processor = QueryProcessor(
        llm_provider=llm_provider,
        embedding_service=embedding_service,
        vector_db=vector_db,
        redis_client=redis_client,
    )

    memory_manager = getattr(app_state, "memory_manager", None)
    memory_service = MemoryService(memory_manager) if memory_manager is not None else None

    tool_registry = _build_tool_registry(
        query_processor=query_processor,
        memory_service=memory_service,
    )
    app_state.tool_registry = tool_registry

    tool_manager = ToolManager(registry=tool_registry, metrics=ToolMetrics())

    compiled_graph = build_agent_graph(
        llm_provider=llm_provider,
        query_processor=query_processor,
        tool_manager=tool_manager,
    )

    logger.info("langgraph_supervisor_init_ok", message="LangGraph graph compiled and cached")
    return compiled_graph


# ---------------------------------------------------------------------------
# Lifespan context manager
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Manages application startup and graceful shutdown.

    Every infrastructure component is wrapped in its own try/except so that a
    single failing dependency does not prevent the server from starting — the
    /health endpoint will surface the degraded state.
    """
    # ---- 1. Structured logging ----
    setup_logging(settings.ENVIRONMENT)
    logger.info("startup_begin", environment=settings.ENVIRONMENT, version="1.0.0")

    # ---- 2. PostgreSQL ----
    try:
        _init_postgres()
    except Exception as exc:
        logger.error("postgres_init_failed", error=str(exc))

    # ---- 3. Redis ----
    try:
        _init_redis()
    except Exception as exc:
        logger.error("redis_init_failed", error=str(exc))

    # ---- 4. Qdrant ----
    try:
        _init_qdrant()
    except Exception as exc:
        logger.error("qdrant_init_failed", error=str(exc))

    # ---- 5. Memory Manager ----
    try:
        app.state.memory_manager = _build_memory_manager()
    except Exception as exc:
        app.state.memory_manager = None
        logger.warning("memory_manager_init_failed", error=str(exc))

    # ---- 6. Tool Registry & LangGraph Supervisor ----
    try:
        app.state.agent_graph = _build_langgraph_supervisor(app.state)
    except Exception as exc:
        app.state.agent_graph = None
        logger.warning("langgraph_supervisor_init_failed", error=str(exc))
        # Fallback tool registry if supervisor initialization failed
        try:
            if not getattr(app.state, "tool_registry", None):
                from src.application.services.memory_service import MemoryService
                mem_svc = MemoryService(app.state.memory_manager) if app.state.memory_manager else None
                app.state.tool_registry = _build_tool_registry(memory_service=mem_svc)
        except Exception:
            app.state.tool_registry = None

    logger.info("startup_complete", message="Application is ready to serve requests")

    yield  # ← server is running

    # ---- Graceful shutdown ----
    logger.info("shutdown_begin", message="Shutting down application...")

    # Release Memory Manager database session
    try:
        if getattr(app.state, "memory_manager", None) is not None:
            repo = getattr(app.state.memory_manager, "_repo", None)
            if repo is not None:
                session = getattr(repo, "_session", None)
                if session is not None:
                    session.close()
    except Exception as exc:
        logger.warning("shutdown_memory_session_close_failed", error=str(exc))

    logger.info("shutdown_complete", message="Application stopped cleanly")


# ---------------------------------------------------------------------------
# FastAPI application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Software Engineering AI Agent API",
    description=(
        "A multi-agent system for automated software engineering tasks. "
        "Powered by a LangGraph Supervisor orchestrating specialised agents "
        "(Planner, Context, Code Analysis, Bug Detection, Security Review, "
        "Performance, Documentation, Test Generation, Code Review, Evaluation) "
        "with Retrieval-Augmented Generation (RAG), Intelligent Memory "
        "(PostgreSQL + Qdrant + Redis), and Tool Calling capabilities."
    ),
    version="1.0.0",
    contact={
        "name": "Software Engineering AI Agent",
        "url": "https://github.com/your-org/software-engineering-ai-agent",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {
            "name": "Health",
            "description": "Service health checks for all infrastructure dependencies.",
        },
        {
            "name": "RAG",
            "description": "Retrieval-Augmented Generation pipeline: ingest, query, and evaluate.",
        },
        {
            "name": "Agents",
            "description": "LangGraph multi-agent workflow execution endpoints.",
        },
        {
            "name": "Memory",
            "description": "Intelligent memory management: short-term, long-term, episodic, and repository memories.",
        },
    ],
    lifespan=lifespan,
    # Disable default 422 response in favour of our custom handler
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Middleware (applied in reverse LIFO order — last registered runs first / outermost)
# ---------------------------------------------------------------------------

# 1. Process time — injects latency header for client-side observability
app.add_middleware(ProcessTimeMiddleware)

# 2. Request ID — stamped on every inbound request and echoed in response
app.add_middleware(RequestIDMiddleware)

# 3. CORS — registered last so it is outermost and guarantees CORS headers on all responses (including errors)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Mx-ReqToken",
        "Keep-Alive",
        "X-Requested-With",
        "If-Modified-Since",
        "X-Request-ID",
        "X-Process-Time-Ms",
        "X-User-ID",  # custom header sent by the frontend API client
    ],
    expose_headers=["X-Request-ID", "X-Process-Time-Ms"],
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(LLMQuotaExceededError, llm_quota_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(APIError, api_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, global_exception_handler)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(api_router, prefix="/api/v1")

# ---------------------------------------------------------------------------
# Root redirect → Swagger UI
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect bare root to the interactive API documentation."""
    return RedirectResponse(url="/docs")


# ---------------------------------------------------------------------------
# Application-level health endpoint (lightweight — no DB round-trips)
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    tags=["Health"],
    summary="Application liveness probe",
    description="Fast liveness check — returns 200 as long as the process is alive.",
)
async def app_health() -> dict:
    """Lightweight liveness probe for container orchestration (Kubernetes, ECS, etc.)."""
    return {
        "status": "alive",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=False)
