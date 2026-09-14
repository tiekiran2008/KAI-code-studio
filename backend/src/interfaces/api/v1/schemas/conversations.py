"""
Conversation Schemas
====================
Pydantic schemas for AI Assistant conversation sessions and chat messages.
Supports both camelCase and snake_case for frontend/backend ergonomics.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatMessageSchema(BaseModel):
    id: str
    session_id: Optional[str] = None
    role: str
    content: str
    agentTraces: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    citations: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    toolCalls: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    timestamp: Optional[str] = None
    created_at: Optional[str] = None


class ConversationSessionSummarySchema(BaseModel):
    id: str
    title: str
    repositoryId: Optional[str] = None
    repository_id: Optional[str] = None
    createdAt: str
    updatedAt: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    message_count: int = 0


class ConversationSessionDetailSchema(BaseModel):
    id: str
    title: str
    repositoryId: Optional[str] = None
    repository_id: Optional[str] = None
    createdAt: str
    updatedAt: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    messages: List[ChatMessageSchema] = Field(default_factory=list)


class CreateSessionRequest(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = "AI Engineering Session"
    repository_id: Optional[str] = None
    repositoryId: Optional[str] = None


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None


class AddMessageRequest(BaseModel):
    id: Optional[str] = None
    role: str
    content: str
    agent_traces: Optional[List[Dict[str, Any]]] = None
    agentTraces: Optional[List[Dict[str, Any]]] = None
    citations: Optional[List[Dict[str, Any]]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    toolCalls: Optional[List[Dict[str, Any]]] = None
