from sqlalchemy import Column, String, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from src.infrastructure.persistence.base import Base

class DBWorkspace(Base):
    __tablename__ = "workspaces"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    default_ai_model = Column(String, default="gpt-4o")
    default_repo_id = Column(
        String,
        ForeignKey("repositories.id", ondelete="SET NULL", use_alter=True, name="fk_workspaces_default_repo_id"),
        nullable=True,
    )
    vector_db_config = Column(JSON, default=dict)
    tool_config = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    repositories = relationship("DBRepository", back_populates="workspace", cascade="all, delete", foreign_keys="[DBRepository.workspace_id]")
    default_repo = relationship("DBRepository", foreign_keys=[default_repo_id])
