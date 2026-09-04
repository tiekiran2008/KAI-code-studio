"""
GitHub Integration ORM Model
=============================
Stores connected GitHub account metadata and encrypted access tokens.
Strictly isolates tokens per KAI user.
"""
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Text, func
from src.infrastructure.persistence.base import Base


class DBGitHubIntegration(Base):
    __tablename__ = "github_integrations"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, unique=True, index=True)
    github_user_id = Column(String, nullable=True)
    github_username = Column(String, nullable=True, index=True)
    avatar_url = Column(String, nullable=True)
    access_token_encrypted = Column(Text, nullable=True)
    token_type = Column(String, default="bearer")
    scope = Column(String, nullable=True)
    connected_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
