"""
Code Review ORM Persistence Models
==================================
SQLAlchemy models for Code Reviews and Findings.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Float, Integer, func
from sqlalchemy.orm import relationship
from .security_finding_models import DBSecurityFinding


from src.infrastructure.persistence.base import Base


class DBCodeReview(Base):
    __tablename__ = "code_reviews"

    id               = Column(String, primary_key=True)
    repository_id    = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id          = Column(String, nullable=False, index=True)
    status           = Column(String, nullable=False, default="pending")  # pending, in_progress, completed, failed
    progress_percent = Column(Integer, default=0, nullable=True)
    current_stage    = Column(String, default="queued", nullable=True)
    progress_message = Column(String, nullable=True)
    
    # Store findings as JSON since they are document-like and queried together
    # Security findings are stored in a separate table linked via relationship
    findings_json    = Column(JSON, default=list)
    performance_findings_json = Column(JSON, default=list)
    confidence_score = Column(Float, default=1.0)
    duration_ms      = Column(Integer, nullable=True)
    performance_score = Column(Float, default=0.0)
    performance_recommendations_json = Column(JSON, default=list)
    estimated_cpu_savings = Column(Float, default=0.0)
    estimated_memory_savings = Column(Float, default=0.0)
    estimated_latency_improvement = Column(Float, default=0.0)

    # Phase 11.4 – Refactoring Analysis
    refactoring_findings_json = Column(JSON, default=list)
    refactoring_priority = Column(String, nullable=True)           # overall priority: critical / high / medium / low
    estimated_refactoring_effort = Column(Float, default=0.0)      # estimated hours
    estimated_maintainability_improvement = Column(Float, default=0.0)  # 0.0 – 100.0
    estimated_technical_debt_reduction = Column(Float, default=0.0)    # estimated debt reduction (hours or %)
    estimated_complexity_reduction = Column(Float, default=0.0)        # estimated complexity reduction (%)

    # Phase 11.5 – Architecture & Code Quality Analysis
    architecture_findings_json = Column(JSON, default=list)
    overall_health_score = Column(Float, default=0.0)        # 0.0 – 100.0
    architecture_score = Column(Float, default=0.0)          # 0.0 – 100.0
    maintainability_score = Column(Float, default=0.0)       # 0.0 – 100.0
    technical_debt_score = Column(Float, default=0.0)        # 0.0 – 100.0
    complexity_score = Column(Float, default=0.0)            # 0.0 – 100.0
    documentation_score = Column(Float, default=0.0)         # 0.0 – 100.0
    modularity_score = Column(Float, default=0.0)             # 0.0 – 100.0
    testability_score = Column(Float, default=0.0)            # 0.0 – 100.0
    dependency_analysis_json = Column(JSON, default=dict)

    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())
    # Relationship to security findings
    security_findings = relationship('DBSecurityFinding', back_populates='review', cascade='all, delete-orphan')
