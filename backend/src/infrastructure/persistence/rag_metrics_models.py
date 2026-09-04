"""
RAG Metrics Persistence Models
================================
SQLAlchemy ORM models for storing RAG query metrics and session data.
These track every query's performance for monitoring and evaluation.
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DBRAGSession(Base):
    """Persistent conversation session — turns are serialised as JSON."""
    __tablename__ = "rag_sessions"

    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, index=True, unique=True)
    repo_id = Column(String, nullable=False, index=True)
    turns_json = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class DBRAGQueryMetrics(Base):
    """One row per RAG query — used for latency monitoring and evaluation."""
    __tablename__ = "rag_query_metrics"

    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    repo_id = Column(String, nullable=False, index=True)
    intent = Column(String, nullable=False)
    original_query = Column(Text, nullable=False)
    retrieval_time_ms = Column(Float, nullable=False)
    rerank_time_ms = Column(Float, nullable=False, default=0.0)
    context_build_time_ms = Column(Float, nullable=False, default=0.0)
    llm_time_ms = Column(Float, nullable=False, default=0.0)
    total_latency_ms = Column(Float, nullable=False)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    num_retrieved_docs = Column(Integer, nullable=False, default=0)
    confidence = Column(Float, nullable=False, default=0.0)
    is_cached = Column(String, nullable=False, default="false")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DBRAGEvaluation(Base):
    """Stores evaluation run results for offline quality measurement."""
    __tablename__ = "rag_evaluations"

    id = Column(String, primary_key=True)
    query = Column(Text, nullable=False)
    intent = Column(String, nullable=False)
    retrieval_precision = Column(Float, nullable=False, default=0.0)
    retrieval_recall = Column(Float, nullable=False, default=0.0)
    answer_relevance = Column(Float, nullable=False, default=0.0)
    groundedness = Column(Float, nullable=False, default=0.0)
    latency_ms = Column(Float, nullable=False, default=0.0)
    num_retrieved = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
