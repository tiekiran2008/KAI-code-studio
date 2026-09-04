from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.domain.entities.user_profile import UserProfile, UserProfileUpdate
from src.application.services.user_profile_service import UserProfileService
from src.interfaces.api.dependencies import get_current_user

# We need a dependency to get the DB session
# Assuming we can create one or import one. The main app uses create_engine.
# We will create a local dependency for the DB session.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.config import settings

router = APIRouter(prefix="/profile", tags=["profile"])

engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_profile_service(db: Session = Depends(get_db)) -> UserProfileService:
    return UserProfileService(db)

@router.get("", response_model=UserProfile)
def get_user_profile(
    current_user: dict = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_profile_service)
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    return profile_service.get_profile(user_id)

@router.put("", response_model=UserProfile)
def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: dict = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_profile_service)
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    
    return profile_service.update_profile(user_id, profile_data)
