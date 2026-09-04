import uuid
from typing import Optional
from sqlalchemy.orm import Session
from src.domain.entities.user_profile import UserProfile, NotificationPreferences, UserProfileUpdate
from src.infrastructure.persistence.user_profile_models import DBUserProfile

class UserProfileService:
    def __init__(self, session: Session):
        self.session = session

    def get_profile(self, user_id: str) -> UserProfile:
        db_profile = self.session.query(DBUserProfile).filter(DBUserProfile.user_id == user_id).first()
        if not db_profile:
            # Create a default profile if none exists
            db_profile = DBUserProfile(
                id=str(uuid.uuid4()),
                user_id=user_id,
                notification_preferences=NotificationPreferences().model_dump()
            )
            self.session.add(db_profile)
            self.session.commit()
            self.session.refresh(db_profile)

        return UserProfile.model_validate(db_profile)

    def update_profile(self, user_id: str, profile_data: UserProfileUpdate) -> UserProfile:
        db_profile = self.session.query(DBUserProfile).filter(DBUserProfile.user_id == user_id).first()
        if not db_profile:
            db_profile = DBUserProfile(
                id=str(uuid.uuid4()),
                user_id=user_id
            )
            self.session.add(db_profile)

        # Update fields
        if profile_data.name is not None:
            db_profile.name = profile_data.name
        if profile_data.avatar is not None:
            db_profile.avatar = profile_data.avatar
        if profile_data.bio is not None:
            db_profile.bio = profile_data.bio
        if profile_data.timezone is not None:
            db_profile.timezone = profile_data.timezone
        if profile_data.theme_preference is not None:
            db_profile.theme_preference = profile_data.theme_preference
        if profile_data.preferred_llm_provider is not None:
            db_profile.preferred_llm_provider = profile_data.preferred_llm_provider
        if profile_data.default_ai_model is not None:
            db_profile.default_ai_model = profile_data.default_ai_model
        if profile_data.notification_preferences is not None:
            db_profile.notification_preferences = profile_data.notification_preferences.model_dump()

        self.session.commit()
        self.session.refresh(db_profile)
        
        return UserProfile.model_validate(db_profile)
