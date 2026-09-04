from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class User(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserSession(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    expires_at: Optional[int] = None
    user: User
    message: Optional[str] = None
    confirmation_required: Optional[bool] = False

