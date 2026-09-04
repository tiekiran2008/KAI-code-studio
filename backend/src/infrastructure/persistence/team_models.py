"""
Team Collaboration & RBAC ORM Persistence Models
=================================================
SQLAlchemy models for Teams, Team Members, Invitations, and Audit Logs.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship

from src.infrastructure.persistence.base import Base


class DBTeam(Base):
    __tablename__ = "teams"

    id          = Column(String, primary_key=True)
    name        = Column(String, nullable=False)
    description = Column(String, nullable=True)
    owner_id    = Column(String, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    members     = relationship("DBTeamMember", back_populates="team", cascade="all, delete-orphan")
    invitations = relationship("DBInvitation", back_populates="team", cascade="all, delete-orphan")
    audit_logs  = relationship("DBAuditLog", back_populates="team", cascade="all, delete-orphan")


class DBTeamMember(Base):
    __tablename__ = "team_members"

    id        = Column(String, primary_key=True)
    team_id   = Column(String, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id   = Column(String, nullable=False, index=True)
    role      = Column(String, nullable=False, default="developer")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    team = relationship("DBTeam", back_populates="members")


class DBInvitation(Base):
    __tablename__ = "invitations"

    id         = Column(String, primary_key=True)
    team_id    = Column(String, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    email      = Column(String, nullable=False, index=True)
    role       = Column(String, nullable=False, default="developer")
    token      = Column(String, nullable=False, unique=True, index=True)
    status     = Column(String, nullable=False, default="pending")  # pending | accepted | rejected | expired
    invited_by = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    team = relationship("DBTeam", back_populates="invitations")


class DBAuditLog(Base):
    __tablename__ = "audit_logs"

    id           = Column(String, primary_key=True)
    team_id      = Column(String, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id     = Column(String, nullable=False, index=True)
    action       = Column(String, nullable=False)
    target_type  = Column(String, nullable=False)
    target_id    = Column(String, nullable=True)
    details_json = Column(JSON, default=dict)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    team = relationship("DBTeam", back_populates="audit_logs")
