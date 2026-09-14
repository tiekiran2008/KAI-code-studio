"""
Conversation API Router
=======================
FastAPI endpoints for managing AI Assistant conversation sessions and messages.
Enforces user isolation across all operations.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.interfaces.api.dependencies import get_db_session, get_current_user
from src.infrastructure.repositories.conversation_repository import ConversationRepository
from src.application.services.conversation_service import ConversationService
from src.interfaces.api.v1.schemas.conversations import (
    ChatMessageSchema,
    ConversationSessionSummarySchema,
    ConversationSessionDetailSchema,
    CreateSessionRequest,
    UpdateSessionRequest,
    AddMessageRequest,
)
from src.core.logger import logger

router = APIRouter(prefix="/conversations", tags=["Conversations"])


def get_conversation_service(db: Session = Depends(get_db_session)) -> ConversationService:
    repo = ConversationRepository(db)
    return ConversationService(repo)


def _get_user_id(current_user: dict) -> str:
    user_id = current_user.get("sub") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user authentication")
    return user_id


@router.get(
    "",
    response_model=List[ConversationSessionSummarySchema],
    summary="List all conversation sessions for the current user",
)
def list_conversations(
    repository_id: Optional[str] = Query(None, description="Filter by repository ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> List[ConversationSessionSummarySchema]:
    user_id = _get_user_id(current_user)
    sessions = service.list_sessions(
        user_id=user_id,
        repository_id=repository_id,
        limit=limit,
        offset=offset,
    )
    return [ConversationSessionSummarySchema(**s) for s in sessions]


@router.post(
    "",
    response_model=ConversationSessionDetailSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation session",
)
def create_conversation(
    request: CreateSessionRequest,
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationSessionDetailSchema:
    user_id = _get_user_id(current_user)
    repo_id = request.repository_id or request.repositoryId
    session = service.create_session(
        user_id=user_id,
        title=request.title or "AI Engineering Session",
        repository_id=repo_id,
        session_id=request.id,
    )
    return ConversationSessionDetailSchema(**session)


@router.get(
    "/{session_id}",
    response_model=ConversationSessionDetailSchema,
    summary="Get conversation session details with full message history",
)
def get_conversation(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationSessionDetailSchema:
    user_id = _get_user_id(current_user)
    session = service.get_session(user_id=user_id, session_id=session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found")
    return ConversationSessionDetailSchema(**session)


@router.patch(
    "/{session_id}",
    summary="Update conversation session title",
)
def update_conversation(
    session_id: str,
    request: UpdateSessionRequest,
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    user_id = _get_user_id(current_user)
    session = service.update_session(user_id=user_id, session_id=session_id, title=request.title)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found")
    return session


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation session",
)
def delete_conversation(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    user_id = _get_user_id(current_user)
    deleted = service.delete_session(user_id=user_id, session_id=session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found")


@router.post(
    "/{session_id}/messages",
    response_model=ChatMessageSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a message to a conversation session",
)
def add_message(
    session_id: str,
    request: AddMessageRequest,
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> ChatMessageSchema:
    user_id = _get_user_id(current_user)
    agent_traces = request.agent_traces if request.agent_traces is not None else request.agentTraces
    tool_calls = request.tool_calls if request.tool_calls is not None else request.toolCalls
    
    msg = service.add_message(
        user_id=user_id,
        session_id=session_id,
        role=request.role,
        content=request.content,
        agent_traces=agent_traces,
        citations=request.citations,
        tool_calls=tool_calls,
        msg_id=request.id,
    )
    return ChatMessageSchema(**msg)


@router.delete(
    "/{session_id}/messages",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear all messages in a conversation session",
)
def clear_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    user_id = _get_user_id(current_user)
    cleared = service.clear_messages(user_id=user_id, session_id=session_id)
    if not cleared:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found")
