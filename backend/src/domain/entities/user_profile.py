from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

class NotificationPreferences(BaseModel):
    email: bool = True
    in_app: bool = True

class UserProfile(BaseModel):
    id: Optional[str] = None
    user_id: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    timezone: str = "UTC"
    theme_preference: str = "system" # system, dark, light
    preferred_llm_provider: str = "openai" # openai, gemini, anthropic
    default_ai_model: str = "gpt-4o"
    notification_preferences: NotificationPreferences = NotificationPreferences()
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    timezone: Optional[str] = None
    theme_preference: Optional[str] = None
    preferred_llm_provider: Optional[str] = None
    default_ai_model: Optional[str] = None
    notification_preferences: Optional[NotificationPreferences] = None
