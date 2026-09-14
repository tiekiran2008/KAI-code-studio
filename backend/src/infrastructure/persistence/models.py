"""
Core SQLAlchemy ORM Models
============================
Central models file. Extended DBRepository for Phase 10.4 (Repository Management).
All side-effect imports at the bottom register sub-module models into shared Base.metadata.
"""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, JSON, String, Text, func
)
from sqlalchemy.orm import relationship
from src.infrastructure.persistence.base import Base
from src.infrastructure.persistence.security_finding_models import DBSecurityFinding


class DBRepository(Base):
    __tablename__ = "repositories"

    # ---------------------------------------------------------------
    # Identity & ownership
    # ---------------------------------------------------------------
    id           = Column(String, primary_key=True)
    user_id      = Column(String, nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)

    # ---------------------------------------------------------------
    # Source information
    # ---------------------------------------------------------------
    url          = Column(String, nullable=False)
    provider     = Column(String, default="github", server_default="github", nullable=False)          # github | gitlab | bitbucket | local
    name         = Column(String, nullable=False)
    description  = Column(Text, nullable=True)
    owner        = Column(String, nullable=True)
    clone_url    = Column(String, nullable=True)
    is_private   = Column(Boolean, default=False)
    stars        = Column(Integer, nullable=True)

    # ---------------------------------------------------------------
    # Branch management
    # ---------------------------------------------------------------
    default_branch = Column(String, default="main")
    current_branch = Column(String, default="main")
    branches_json  = Column(JSON, default=list)           # ["main", "dev", "feature/x"]

    # ---------------------------------------------------------------
    # Size & metrics
    # ---------------------------------------------------------------
    repo_size_kb  = Column(Integer, nullable=True)
    chunks_count  = Column(Integer, default=0)

    # ---------------------------------------------------------------
    # AI-detected stack (Phase 10.4)
    # ---------------------------------------------------------------
    language_stats_json  = Column(JSON, default=list)     # [{"language": "Python", "percentage": 80, "bytes": 12000}]
    detected_stack_json  = Column(JSON, default=dict)     # DetectedStack serialised

    # ---------------------------------------------------------------
    # Indexing pipeline state
    # ---------------------------------------------------------------
    indexing_status = Column(String, default="pending")   # pending|indexing|indexed|failed|stale
    indexing_error  = Column(Text, nullable=True)
    last_indexed_at = Column(DateTime(timezone=True), nullable=True)

    # ---------------------------------------------------------------
    # Security (encrypted PAT for private repos)
    # ---------------------------------------------------------------
    git_access_token_encrypted = Column(Text, nullable=True)

    # ---------------------------------------------------------------
    # Timestamps
    # ---------------------------------------------------------------
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ---------------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------------
    workspace = relationship(
        "DBWorkspace",
        back_populates="repositories",
        foreign_keys=[workspace_id],
    )
    files = relationship("DBSourceFile", back_populates="repository", cascade="all, delete-orphan")
    projects = relationship(
        "DBProject",
        secondary="project_repositories",
        back_populates="repositories",
        lazy="select",
    )


class DBSourceFile(Base):
    __tablename__ = "source_files"

    id      = Column(String, primary_key=True)
    repo_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"))
    path    = Column(String, nullable=False)
    language = Column(String, nullable=False)

    repository = relationship("DBRepository", back_populates="files")
    symbols    = relationship("DBCodeSymbol", back_populates="source_file", cascade="all, delete-orphan")


class DBCodeSymbol(Base):
    __tablename__ = "code_symbols"

    id          = Column(String, primary_key=True)
    file_id     = Column(String, ForeignKey("source_files.id", ondelete="CASCADE"))
    name        = Column(String, nullable=False)
    symbol_type = Column(String, nullable=False)
    start_line  = Column(Integer, nullable=False)
    end_line    = Column(Integer, nullable=False)
    metadata_json = Column(JSON, nullable=True)   # docstrings, complexity

    source_file = relationship("DBSourceFile", back_populates="symbols")


# ---------------------------------------------------------------------------
# Side-effect imports — register sub-module models into shared metadata
# ---------------------------------------------------------------------------
from src.infrastructure.persistence.rag_metrics_models import DBRAGSession, DBRAGQueryMetrics, DBRAGEvaluation  # noqa: F401, E402
from src.infrastructure.persistence.memory_models import DBMemory                                                # noqa: F401, E402
from src.infrastructure.persistence.user_profile_models import DBUserProfile                                     # noqa: F401, E402
from src.infrastructure.persistence.workspace_models import DBWorkspace                                          # noqa: F401, E402
from src.infrastructure.persistence.project_models import DBProject, DBProjectRepository                         # noqa: F401, E402
from src.infrastructure.persistence.team_models import DBTeam, DBTeamMember, DBInvitation, DBAuditLog             # noqa: F401, E402
from src.infrastructure.persistence.code_review_models import DBCodeReview                                       # noqa: F401, E402
from src.infrastructure.persistence.report_models import DBReport                                                # noqa: F401, E402
from src.infrastructure.persistence.github_models import DBGitHubIntegration                                     # noqa: F401, E402
from src.infrastructure.persistence.conversation_models import DBConversationSession, DBConversationMessage     # noqa: F401, E402

