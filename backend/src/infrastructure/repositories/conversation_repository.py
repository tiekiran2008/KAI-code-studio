"""
Conversation Repository
=======================
SQLAlchemy repository implementation for managing Conversation Sessions and Messages.
Enforces strict user isolation.
"""
from datetime import datetime, timezone
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.infrastructure.persistence.conversation_models import (
    DBConversationSession,
    DBConversationMessage,
)
from src.core.logger import logger


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_sessions(
        self,
        user_id: str,
        repository_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DBConversationSession]:
        """List conversation sessions for a user, ordered by most recently updated."""
        query = self.db.query(DBConversationSession).filter(
            DBConversationSession.user_id == user_id
        )
        if repository_id:
            query = query.filter(DBConversationSession.repository_id == repository_id)
        
        return (
            query.order_by(desc(DBConversationSession.updated_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_session(self, user_id: str, session_id: str) -> Optional[DBConversationSession]:
        """Fetch a specific conversation session along with its messages, strictly scoped to user_id."""
        return (
            self.db.query(DBConversationSession)
            .filter(
                DBConversationSession.id == session_id,
                DBConversationSession.user_id == user_id,
            )
            .first()
        )

    def create_session(
        self,
        user_id: str,
        title: str = "AI Engineering Session",
        repository_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> DBConversationSession:
        """Create a new conversation session for the user."""
        sid = session_id or f"session-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        
        # Check if already exists (idempotency)
        existing = self.get_session(user_id, sid)
        if existing:
            return existing

        session_obj = DBConversationSession(
            id=sid,
            user_id=user_id,
            repository_id=repository_id,
            title=title or "AI Engineering Session",
            created_at=now,
            updated_at=now,
        )
        self.db.add(session_obj)
        self.db.commit()
        self.db.refresh(session_obj)
        logger.info("conversation_session_created", session_id=sid, user_id=user_id)
        return session_obj

    def update_session(
        self,
        user_id: str,
        session_id: str,
        title: Optional[str] = None,
    ) -> Optional[DBConversationSession]:
        """Update session metadata."""
        session_obj = self.get_session(user_id, session_id)
        if not session_obj:
            return None

        if title is not None:
            session_obj.title = title
        session_obj.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(session_obj)
        return session_obj

    def delete_session(self, user_id: str, session_id: str) -> bool:
        """Delete a conversation session and all its messages."""
        session_obj = self.get_session(user_id, session_id)
        if not session_obj:
            return False

        self.db.delete(session_obj)
        self.db.commit()
        logger.info("conversation_session_deleted", session_id=session_id, user_id=user_id)
        return True

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
    ) -> DBConversationMessage:
        """
        Append a message to a session. Auto-creates the session if not yet present.
        Updates session updated_at timestamp.
        """
        session_obj = self.get_session(user_id, session_id)
        if not session_obj:
            # Auto-create session if missing
            title = (content[:40] + "...") if content else "AI Engineering Session"
            session_obj = self.create_session(
                user_id=user_id,
                title=title,
                session_id=session_id,
            )

        mid = msg_id or f"msg-{uuid.uuid4().hex[:12]}"
        
        # Check if message already exists with this ID to prevent duplicate messages
        existing_msg = (
            self.db.query(DBConversationMessage)
            .filter(
                DBConversationMessage.id == mid,
                DBConversationMessage.session_id == session_id,
            )
            .first()
        )
        if existing_msg:
            return existing_msg

        now = datetime.now(timezone.utc)
        message_obj = DBConversationMessage(
            id=mid,
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            agent_traces_json=agent_traces or [],
            citations_json=citations or [],
            tool_calls_json=tool_calls or [],
            created_at=now,
        )
        self.db.add(message_obj)

        # Update session title if it's the first user message and default title
        if role == "user" and session_obj.title == "AI Engineering Session" and content:
            session_obj.title = content[:50].strip()

        session_obj.updated_at = now
        self.db.commit()
        self.db.refresh(message_obj)
        return message_obj

    def clear_session_messages(self, user_id: str, session_id: str) -> bool:
        """Delete all messages inside a session without deleting the session container."""
        session_obj = self.get_session(user_id, session_id)
        if not session_obj:
            return False

        self.db.query(DBConversationMessage).filter(
            DBConversationMessage.session_id == session_id,
            DBConversationMessage.user_id == user_id,
        ).delete()
        session_obj.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        return True
