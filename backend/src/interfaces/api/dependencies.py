"""
API Dependency Injection
========================
FastAPI dependency factories for all injectable services.
Uses module-level singletons for expensive objects (LLM provider, embedding
model) and per-request scoping for DB sessions.
"""
from typing import Any, Generator, Optional
from functools import lru_cache

import redis
from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.core.config import settings
from src.core.logger import logger


# ---------------------------------------------------------------------------
# Infrastructure singletons (module-level, initialised once)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_embedding_service():
    """Cached SentenceTransformer embedding service (expensive to load)."""
    from src.infrastructure.embeddings.sentence_transformer_service import SentenceTransformerService
    logger.info("embedding_service_init", message="Loading SentenceTransformer modelâ€¦")
    return SentenceTransformerService()


@lru_cache(maxsize=1)
def _get_vector_db():
    """Cached Qdrant adapter."""
    from src.infrastructure.vector_db.qdrant_adapter import QdrantAdapter
    return QdrantAdapter(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)


@lru_cache(maxsize=1)
def _get_llm_provider():
    """Cached LLM provider — raises LLMConfigurationError if no key present."""
    from src.infrastructure.llm.llm_factory import create_llm_provider
    return create_llm_provider()


@lru_cache(maxsize=1)
def _get_db_engine():
    return create_engine(settings.POSTGRES_URL, pool_pre_ping=True)


@lru_cache(maxsize=1)
def _get_session_factory():
    return sessionmaker(autocommit=False, autoflush=False, bind=_get_db_engine())


# ---------------------------------------------------------------------------
# Per-request dependencies
# ---------------------------------------------------------------------------

def get_redis_client() -> Generator[redis.Redis, None, None]:
    """Dependency for injecting a Redis client."""
    client = redis.from_url(settings.REDIS_URL, **settings.get_redis_kwargs())
    try:
        yield client
    finally:
        client.close()


def get_db_session() -> Generator[Session, None, None]:
    """Dependency for injecting an SQLAlchemy session."""
    factory = _get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# RAG pipeline dependencies
# ---------------------------------------------------------------------------

def get_conversation_manager(
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """ConversationManager with injected Redis client."""
    from src.application.rag.conversation_manager import ConversationManager
    return ConversationManager(redis_client)


def get_rag_use_case(
    redis_client: redis.Redis = Depends(get_redis_client),
    db_session: Session = Depends(get_db_session),
):
    """Fully-wired RAGQueryUseCase."""
    from src.application.rag.query_processor import QueryProcessor
    from src.application.use_cases.rag_query import RAGQueryUseCase

    processor = QueryProcessor(
        llm_provider=_get_llm_provider(),
        embedding_service=_get_embedding_service(),
        vector_db=_get_vector_db(),
        redis_client=redis_client,
    )
    return RAGQueryUseCase(processor=processor, db_session=db_session)


def get_evaluate_rag_use_case(
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """Fully-wired EvaluateRAGUseCase."""
    from src.application.rag.query_processor import QueryProcessor
    from src.application.use_cases.evaluate_rag import EvaluateRAGUseCase

    processor = QueryProcessor(
        llm_provider=_get_llm_provider(),
        embedding_service=_get_embedding_service(),
        vector_db=_get_vector_db(),
        redis_client=redis_client,
    )
    return EvaluateRAGUseCase(processor=processor)



def get_tool_manager(
    memory_svc=None,
    query_processor=None,
    github_token_resolver=None,
) -> Any:
    """Instantiate the Tool Registry, register adapters, and return the Tool Manager.

    Parameters
    ----------
    github_token_resolver : Optional[Callable[[], Optional[str]]]
        Zero-argument callable that returns the current user's GitHub OAuth token.
        When provided, the GitHubToolAdapter performs per-execution token resolution
        without holding the token in memory beyond the execute() call scope.
    """
    from src.infrastructure.tools.registry import ToolRegistry
    from src.infrastructure.tools.manager import ToolManager
    from src.infrastructure.observability.tool_metrics import ToolMetrics
    from src.infrastructure.tools.adapters.github import GitHubToolAdapter
    from src.infrastructure.tools.adapters.local_fs import LocalFileSystemAdapter
    from src.infrastructure.tools.adapters.docs import DocumentationSearchAdapter
    from src.infrastructure.tools.adapters.database import DatabaseToolAdapter
    from src.infrastructure.tools.adapters.repo_diff import RepositoryDiffAdapter

    registry = ToolRegistry()
    metrics = ToolMetrics()

    # In a real setup, tokens and paths come from config
    workspace_root = getattr(settings, "WORKSPACE_ROOT", "./workspace")

    # Register adapters
    # Use token_resolver for per-user OAuth scoping; no static dummy token at runtime.
    registry.register(GitHubToolAdapter(token_resolver=github_token_resolver))
    registry.register(LocalFileSystemAdapter(workspace_root=workspace_root))
    registry.register(DocumentationSearchAdapter(query_processor=query_processor))
    registry.register(RepositoryDiffAdapter(workspace_root=workspace_root))

    if memory_svc:
        registry.register(DatabaseToolAdapter(memory_service=memory_svc))

    return ToolManager(registry=registry, metrics=metrics)


def get_agent_use_case(
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """Fully-wired ExecuteAgentWorkflowUseCase with Phase 7 MemoryService and Phase 8 ToolManager."""
    from src.application.rag.query_processor import QueryProcessor
    from src.application.use_cases.agent_execution import ExecuteAgentWorkflowUseCase

    processor = QueryProcessor(
        llm_provider=_get_llm_provider(),
        embedding_service=_get_embedding_service(),
        vector_db=_get_vector_db(),
        redis_client=redis_client,
    )

    # Build memory service (gracefully skip if infrastructure is unavailable)
    memory_svc = None
    try:
        from src.application.services.memory_service import MemoryService
        from src.infrastructure.memory.memory_manager import MemoryManager
        from src.infrastructure.memory.postgres_memory_repository import PostgresMemoryRepository
        from src.infrastructure.memory.qdrant_memory_vector_store import QdrantMemoryVectorStore
        from src.infrastructure.memory.redis_session_cache import RedisSessionCache
        from src.infrastructure.memory.memory_encryptor import FernetMemoryEncryptor
        from src.infrastructure.observability.memory_metrics import MemoryMetrics

        db_session = _get_session_factory()()
        encryptor = FernetMemoryEncryptor(settings.MEMORY_ENCRYPTION_KEY or None)
        repo = PostgresMemoryRepository(db_session, encryptor)
        vector_store = QdrantMemoryVectorStore(
            qdrant_url=settings.QDRANT_URL,
            vector_dim=settings.MEMORY_VECTOR_DIM,
            collection_name=settings.MEMORY_VECTOR_COLLECTION,
        )
        session_cache = RedisSessionCache(redis_client)
        manager = MemoryManager(
            repository=repo,
            vector_store=vector_store,
            session_cache=session_cache,
            embedding_service=_get_embedding_service(),
            metrics=MemoryMetrics(),
            short_term_ttl=settings.MEMORY_SHORT_TERM_TTL_SECONDS,
            long_term_ttl_days=settings.MEMORY_LONG_TERM_TTL_DAYS,
        )
        memory_svc = MemoryService(manager)
    except Exception as exc:
        logger.warning("memory_service_init_skipped", error=str(exc))

    # Build Tool Manager with per-user GitHub token resolver
    def _make_github_token_resolver(svc, uid):
        """Close over the service and user_id to create a zero-arg resolver."""
        def _resolver():
            return svc.get_decrypted_token(uid) if uid else None
        return _resolver

    tool_manager = get_tool_manager(
        memory_svc=memory_svc,
        query_processor=processor,
        github_token_resolver=None,  # agent use case builds without auth context; tools degrade gracefully
    )

    return ExecuteAgentWorkflowUseCase(
        llm_provider=_get_llm_provider(),
        query_processor=processor,
        memory_service=memory_svc,
        tool_manager=tool_manager,
    )


def get_memory_service(
    redis_client: redis.Redis = Depends(get_redis_client),
    db_session=Depends(get_db_session),
):
    """
    Fully-wired MemoryService for the /memory API endpoints.
    Wires PostgreSQL, Qdrant, and Redis into the MemoryManager.
    """
    from src.application.services.memory_service import MemoryService
    from src.infrastructure.memory.memory_manager import MemoryManager
    from src.infrastructure.memory.postgres_memory_repository import PostgresMemoryRepository
    from src.infrastructure.memory.qdrant_memory_vector_store import QdrantMemoryVectorStore
    from src.infrastructure.memory.redis_session_cache import RedisSessionCache
    from src.infrastructure.memory.memory_encryptor import FernetMemoryEncryptor
    from src.infrastructure.observability.memory_metrics import MemoryMetrics

    encryptor = FernetMemoryEncryptor(settings.MEMORY_ENCRYPTION_KEY or None)
    repo = PostgresMemoryRepository(db_session, encryptor)
    vector_store = QdrantMemoryVectorStore(
        qdrant_url=settings.QDRANT_URL,
        vector_dim=settings.MEMORY_VECTOR_DIM,
        collection_name=settings.MEMORY_VECTOR_COLLECTION,
    )
    session_cache = RedisSessionCache(redis_client)
    manager = MemoryManager(
        repository=repo,
        vector_store=vector_store,
        session_cache=session_cache,
        embedding_service=_get_embedding_service(),
        metrics=MemoryMetrics(),
        short_term_ttl=settings.MEMORY_SHORT_TERM_TTL_SECONDS,
        long_term_ttl_days=settings.MEMORY_LONG_TERM_TTL_DAYS,
    )
    return MemoryService(manager)

import uuid
from typing import Optional
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, status
from src.application.services.auth_service import AuthService

security = HTTPBearer(auto_error=False)

class UserPayload(dict):
    @property
    def id(self) -> str:
        return self.get("sub") or ""

    @property
    def email(self) -> str:
        return self.get("email") or ""

def get_auth_service() -> AuthService:
    return AuthService()

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserPayload:
    # Check bypass safety
    is_production = settings.ENVIRONMENT.lower() in ("production", "prod")
    bypass_active = settings.DEV_AUTH_BYPASS and not is_production

    if credentials is None:
        if bypass_active:
            dev_email = settings.DEV_AUTH_USER_EMAIL or "dev-user@example.com"
            dev_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, dev_email))
            return UserPayload(sub=dev_id, email=dev_email)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = auth_service.validate_token(token)
        return UserPayload(payload)
    except ValueError as e:
        if bypass_active:
            dev_email = settings.DEV_AUTH_USER_EMAIL or "dev-user@example.com"
            dev_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, dev_email))
            return UserPayload(sub=dev_id, email=dev_email)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# GitHub Integration Dependencies (defined AFTER get_current_user)
# ---------------------------------------------------------------------------

def get_github_integration_service(
    db_session: Session = Depends(get_db_session),
) -> Any:
    """
    Per-request factory for GitHubIntegrationService.
    Uses the request-scoped DB session so token lookups are isolated to the current request.
    """
    from src.application.services.github_integration_service import GitHubIntegrationService
    return GitHubIntegrationService(db_session)


def get_user_scoped_github_token(
    current_user: Any = Depends(get_current_user),
    github_svc: Any = Depends(get_github_integration_service),
) -> Optional[str]:
    """
    Resolve the current authenticated user's decrypted GitHub OAuth token.

    Returns ``None`` (not an error) if the user has not connected GitHub.
    Callers that require a token must raise their own HTTPException.

    SECURITY: The returned value is a decrypted secret — callers must not
    log it, store it, or include it in any response payload.
    """
    user_id = current_user.get("sub") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    if not user_id:
        return None
    return github_svc.get_decrypted_token(user_id)



@lru_cache(maxsize=1)
def _get_embedding_service_cached():
    """Cached SentenceTransformer embeddings — alias to avoid duplicate lru_cache."""
    return _get_embedding_service()


def get_repository_ingestion_service(db_session: Session = Depends(get_db_session)) -> Any:
    from src.infrastructure.repositories.repository_repository import RepositoryRepository
    from src.application.services.index_manager import IndexManager
    from src.application.services.repository_ingestion_service import RepositoryIngestionService
    repo_repo = RepositoryRepository(db_session)
    vector_db = _get_vector_db()
    emb_svc = _get_embedding_service()
    idx_mgr = IndexManager(emb_svc, vector_db, db_session)
    return RepositoryIngestionService(idx_mgr, repo_repo, session_factory=_get_session_factory)


def get_repository_service(db_session: Session = Depends(get_db_session)) -> Any:
    from src.infrastructure.repositories.repository_repository import RepositoryRepository
    from src.application.services.repository_service import RepositoryService
    from src.application.services.index_manager import IndexManager
    from src.application.services.repository_ingestion_service import RepositoryIngestionService
    repo = RepositoryRepository(db_session)
    vector_db = _get_vector_db()
    emb_svc = _get_embedding_service()
    idx_mgr = IndexManager(emb_svc, vector_db, db_session)
    ingestion_svc = RepositoryIngestionService(idx_mgr, repo, session_factory=_get_session_factory)
    return RepositoryService(repo, ingestion_service=ingestion_svc, vector_db=vector_db)


def get_code_review_service(db_session: Session = Depends(get_db_session)) -> Any:
    from src.infrastructure.repositories.code_review_repository import CodeReviewRepository
    from src.application.services.code_review_service import CodeReviewService
    repo = CodeReviewRepository(db_session)
    return CodeReviewService(repo)


def get_apply_fix_use_case(
    review_svc: Any = Depends(get_code_review_service),
    repo_svc: Any = Depends(get_repository_service),
) -> Any:
    from src.application.use_cases.apply_fix import ApplyFixSuggestionUseCase
    return ApplyFixSuggestionUseCase(
        review_service=review_svc,
        repository_service=repo_svc,
    )


def get_rollback_applied_fix_use_case(
    review_svc: Any = Depends(get_code_review_service),
    repo_svc: Any = Depends(get_repository_service),
) -> Any:
    from src.application.use_cases.rollback_applied_fix import RollbackAppliedFixUseCase
    return RollbackAppliedFixUseCase(
        review_service=review_svc,
        repository_service=repo_svc,
    )


def get_verify_applied_fix_use_case(
    review_svc: Any = Depends(get_code_review_service),
    repo_svc: Any = Depends(get_repository_service),
) -> Any:
    from src.application.use_cases.verify_applied_fix import VerifyAppliedFixUseCase
    return VerifyAppliedFixUseCase(
        review_service=review_svc,
        repository_service=repo_svc,
    )


def get_verify_applied_fix_tests_use_case(
    review_svc: Any = Depends(get_code_review_service),
    repo_svc: Any = Depends(get_repository_service),
) -> Any:
    from src.application.use_cases.verify_applied_fix_tests import VerifyAppliedFixTestsUseCase
    from src.infrastructure.sandbox.sandbox_engine import SandboxExecutionEngine
    return VerifyAppliedFixTestsUseCase(
        review_service=review_svc,
        repository_service=repo_svc,
        sandbox_engine=SandboxExecutionEngine(),
    )


def get_commit_applied_fix_use_case(
    review_svc: Any = Depends(get_code_review_service),
    repo_svc: Any = Depends(get_repository_service),
) -> Any:
    """Dependency factory for CommitAppliedFixUseCase.

    Wires CodeReviewService, RepositoryService, and GitWorkingTreeManager.
    The workspace root is resolved from WORKSPACE_ROOT env var or cwd at request time
    (no absolute path accepted from the client).
    """
    from src.application.use_cases.commit_applied_fix import CommitAppliedFixUseCase
    from src.infrastructure.git.working_tree_manager import GitWorkingTreeManager
    return CommitAppliedFixUseCase(
        review_service=review_svc,
        repository_service=repo_svc,
        working_tree_manager=GitWorkingTreeManager(),
    )


def get_push_fix_branch_use_case(
    review_svc: Any = Depends(get_code_review_service),
    repo_svc: Any = Depends(get_repository_service),
) -> Any:
    """Dependency factory for PushFixBranchUseCase.

    Wires CodeReviewService, RepositoryService, and GitWorkingTreeManager.
    """
    from src.application.use_cases.push_fix_branch import PushFixBranchUseCase
    from src.infrastructure.git.working_tree_manager import GitWorkingTreeManager
    return PushFixBranchUseCase(
        review_service=review_svc,
        repository_service=repo_svc,
        working_tree_manager=GitWorkingTreeManager(),
    )


def get_create_fix_pull_request_use_case(
    current_user: Any = Depends(get_current_user),
    github_svc: Any = Depends(get_github_integration_service),
    review_svc: Any = Depends(get_code_review_service),
    repo_svc: Any = Depends(get_repository_service),
) -> Any:
    """Dependency factory for CreateFixPullRequestUseCase.

    Wires CodeReviewService, RepositoryService, GitHubPullRequestService, and
    the current user's decrypted GitHub OAuth token from GitHubIntegrationService.

    Token resolution priority at PR creation time:
      1. User's connected GitHub OAuth token (GitHubIntegrationService)
      2. Repository-level stored PAT  (git_access_token_encrypted)
      3. GITHUB_TOKEN environment variable

    SECURITY: The token is resolved server-side only, never logged, and never
    returned in any response payload.
    """
    from src.application.use_cases.create_fix_pull_request import CreateFixPullRequestUseCase
    from src.infrastructure.git.github_pr_service import GitHubPullRequestService

    # Resolve the current user's OAuth token now, before the use case is constructed.
    # The token is passed to execute() rather than stored in the use case instance.
    user_id = (
        current_user.get("sub")
        if isinstance(current_user, dict)
        else getattr(current_user, "id", None)
    )
    user_github_token: Optional[str] = None
    if user_id:
        try:
            user_github_token = github_svc.get_decrypted_token(user_id)
        except Exception:
            # Graceful degradation: if integration lookup fails, fall back to stored PAT
            pass

    # Create a thin adapter that injects the per-user token into execute()
    use_case = CreateFixPullRequestUseCase(
        review_service=review_svc,
        repository_service=repo_svc,
        github_pr_service=GitHubPullRequestService(),
    )
    # Wrap execute() to always inject the per-user token transparently.
    # This avoids storing the token in the use case instance.
    _original_execute = use_case.execute

    async def _user_scoped_execute(review_id, finding_index, user_id, **kwargs):
        return await _original_execute(
            review_id=review_id,
            finding_index=finding_index,
            user_id=user_id,
            github_token=user_github_token,  # injected from this request's user context
        )

    use_case.execute = _user_scoped_execute
    return use_case







