"""
Project Persistence Models
============================
SQLAlchemy ORM models for Projects and the Project↔Repository join table.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from src.infrastructure.persistence.base import Base


class DBProjectRepository(Base):
    """Many-to-many join table: project ↔ repository."""
    __tablename__ = "project_repositories"

    project_id    = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), primary_key=True)


class DBProject(Base):
    __tablename__ = "projects"

    id           = Column(String, primary_key=True)
    user_id      = Column(String, nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True)
    name         = Column(String, nullable=False)
    description  = Column(String, nullable=True)
    status       = Column(String, default="active", nullable=False)  # active | archived

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    repositories = relationship(
        "DBRepository",
        secondary="project_repositories",
        back_populates="projects",
        lazy="select",
    )
