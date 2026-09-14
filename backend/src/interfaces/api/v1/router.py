from fastapi import APIRouter
from .health import router as health_router
from .rag import router as rag_router
from .agents import router as agents_router
from .memory import router as memory_router
from .auth import router as auth_router
from .profile import router as profile_router
from .workspaces import router as workspaces_router
from .repositories import router as repositories_router
from .projects import router as projects_router
from .teams import router as teams_router
from .invitations import router as invitations_router
from .reviews import router as reviews_router
from .reports import router as reports_router
from .integrations import router as integrations_router
from .analytics import router as analytics_router
from .conversations import router as conversations_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/health", tags=["Health"])
api_router.include_router(rag_router, prefix="/rag", tags=["RAG"])
api_router.include_router(agents_router, prefix="/agents", tags=["Agents"])
api_router.include_router(memory_router, prefix="/memory", tags=["Memory"])
api_router.include_router(auth_router)  # Prefix is already set in auth.py
api_router.include_router(profile_router)
api_router.include_router(workspaces_router)
api_router.include_router(repositories_router)
api_router.include_router(projects_router)
api_router.include_router(teams_router)
api_router.include_router(invitations_router)
api_router.include_router(reviews_router)
api_router.include_router(reports_router)
api_router.include_router(integrations_router)
api_router.include_router(analytics_router)
api_router.include_router(conversations_router)



