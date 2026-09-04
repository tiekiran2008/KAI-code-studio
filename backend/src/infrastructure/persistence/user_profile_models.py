from sqlalchemy import Column, String, JSON, DateTime, func
from src.infrastructure.persistence.base import Base

class DBUserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=True)
    avatar = Column(String, nullable=True) # Could be URL or Base64
    bio = Column(String, nullable=True)
    timezone = Column(String, default="UTC")
    theme_preference = Column(String, default="system")
    preferred_llm_provider = Column(String, default="openai")
    default_ai_model = Column(String, default="gpt-4o")
    notification_preferences = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
