from sqlalchemy import Column, String, Float, Integer
from src.infrastructure.persistence.base import Base

class DBIndexingMetrics(Base):
    __tablename__ = "indexing_metrics"
    id = Column(String, primary_key=True)
    repo_id = Column(String, nullable=False)
    commit_hash = Column(String, nullable=False)
    indexing_time_sec = Column(Float, nullable=False)
    chunks_created = Column(Integer, nullable=False)
    embedding_latency_sec = Column(Float, nullable=False)
