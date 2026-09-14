"""
Conversation Persistence Models (SQLAlchemy ORM)
=================================================
Defines the PostgreSQL table schemas for AI Assistant conversation sessions
and their structured chat messages.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from src.infrastructure.persistence.base import Base


class DBConversationSession(Base):
    """
    Represents an ongoing or historical conversation session with the AI Assistant.
    Scoped to an authenticated user and optionally linked to a specific repository.
    """
    __tablename__ = "conversation_sessions"

    id            = Column(String(64), primary_key=True, comment="UUID or session identifier")
    user_id       = Column(String(255), nullable=False, index=True, comment="Owner user ID")
    repository_id = Column(String(255), nullable=True, index=True, comment="Scoped repository ID")
    title         = Column(String(255), nullable=False, default="AI Engineering Session")

    created_at    = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    messages      = relationship(
        "DBConversationMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="DBConversationMessage.created_at.asc()",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_conv_session_user_updated", "user_id", "updated_at"),
    )


class DBConversationMessage(Base):
    """
    A single turn / message in a conversation session.
    Stores rich structured agent metadata (execution trace, citations, tool calls).
    """
    __tablename__ = "conversation_messages"

    id                = Column(String(64), primary_key=True, comment="UUID or message identifier")
    session_id        = Column(
        String(64),
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id           = Column(String(255), nullable=False, index=True, comment="Owner user ID")
    role              = Column(String(32), nullable=False, comment="user | assistant | system")
    content           = Column(Text, nullable=False, default="")
    agent_traces_json = Column(JSON, nullable=False, default=list, comment="Agent trace steps")
    citations_json    = Column(JSON, nullable=False, default=list, comment="Source citations")
    tool_calls_json   = Column(JSON, nullable=False, default=list, comment="Executed tool calls")

    created_at        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session           = relationship("DBConversationSession", back_populates="messages")

    __table_args__ = (
        Index("ix_conv_msg_session_created", "session_id", "created_at"),
    )
