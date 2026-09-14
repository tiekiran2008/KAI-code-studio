"""
Conversation Service
====================
Application service coordinating AI Assistant conversation sessions and messages.
"""
from typing import Any, Dict, List, Optional
from src.infrastructure.repositories.conversation_repository import ConversationRepository
from src.infrastructure.persistence.conversation_models import (
    DBConversationSession,
    DBConversationMessage,
)


class ConversationService:
    def __init__(self, repository: ConversationRepository):
        self.repository = repository

    def list_sessions(
        self,
        user_id: str,
        repository_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        sessions = self.repository.list_sessions(
            user_id=user_id,
            repository_id=repository_id,
            limit=limit,
            offset=offset,
        )
        return [
            {
                "id": s.id,
                "title": s.title,
                "repositoryId": s.repository_id,
                "repository_id": s.repository_id,
                "createdAt": s.created_at.isoformat() if s.created_at else "",
                "updatedAt": s.updated_at.isoformat() if s.updated_at else "",
                "created_at": s.created_at.isoformat() if s.created_at else "",
                "updated_at": s.updated_at.isoformat() if s.updated_at else "",
                "message_count": len(s.messages) if s.messages else 0,
            }
            for s in sessions
        ]

    def get_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        session_obj = self.repository.get_session(user_id, session_id)
        if not session_obj:
            return None

        return {
            "id": session_obj.id,
            "title": session_obj.title,
            "repositoryId": session_obj.repository_id,
            "repository_id": session_obj.repository_id,
            "createdAt": session_obj.created_at.isoformat() if session_obj.created_at else "",
            "updatedAt": session_obj.updated_at.isoformat() if session_obj.updated_at else "",
            "created_at": session_obj.created_at.isoformat() if session_obj.created_at else "",
            "updated_at": session_obj.updated_at.isoformat() if session_obj.updated_at else "",
            "messages": [
                {
                    "id": m.id,
                    "session_id": m.session_id,
                    "role": m.role,
                    "content": m.content,
                    "agentTraces": m.agent_traces_json or [],
                    "citations": m.citations_json or [],
                    "toolCalls": m.tool_calls_json or [],
                    "timestamp": m.created_at.isoformat() if m.created_at else "",
                    "created_at": m.created_at.isoformat() if m.created_at else "",
                }
                for m in (session_obj.messages or [])
            ],
        }

    def create_session(
        self,
        user_id: str,
        title: str = "AI Engineering Session",
        repository_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        s = self.repository.create_session(
            user_id=user_id,
            title=title,
            repository_id=repository_id,
            session_id=session_id,
        )
        return {
            "id": s.id,
            "title": s.title,
            "repositoryId": s.repository_id,
            "repository_id": s.repository_id,
            "createdAt": s.created_at.isoformat() if s.created_at else "",
            "updatedAt": s.updated_at.isoformat() if s.updated_at else "",
            "created_at": s.created_at.isoformat() if s.created_at else "",
            "updated_at": s.updated_at.isoformat() if s.updated_at else "",
            "messages": [],
        }

    def update_session(
        self,
        user_id: str,
        session_id: str,
        title: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        s = self.repository.update_session(user_id, session_id, title=title)
        if not s:
            return None
        return {
            "id": s.id,
            "title": s.title,
            "repositoryId": s.repository_id,
            "repository_id": s.repository_id,
            "createdAt": s.created_at.isoformat() if s.created_at else "",
            "updatedAt": s.updated_at.isoformat() if s.updated_at else "",
        }

    def delete_session(self, user_id: str, session_id: str) -> bool:
        return self.repository.delete_session(user_id, session_id)

    def add_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        agent_traces: Optional[list] = None,
        citations: Optional[list] = None,
        tool_calls: Optional[list] = None,
        msg_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        m = self.repository.add_message(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            agent_traces=agent_traces,
            citations=citations,
            tool_calls=tool_calls,
            msg_id=msg_id,
        )
        return {
            "id": m.id,
            "session_id": m.session_id,
            "role": m.role,
            "content": m.content,
            "agentTraces": m.agent_traces_json or [],
            "citations": m.citations_json or [],
            "toolCalls": m.tool_calls_json or [],
            "timestamp": m.created_at.isoformat() if m.created_at else "",
            "created_at": m.created_at.isoformat() if m.created_at else "",
        }

    def clear_messages(self, user_id: str, session_id: str) -> bool:
        return self.repository.clear_session_messages(user_id, session_id)
