import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.api.dependencies import get_current_user
from src.interfaces.api.v1.profile import get_profile_service
from src.domain.entities.user_profile import UserProfile, NotificationPreferences
from src.application.services.user_profile_service import UserProfileService
from src.infrastructure.persistence.user_profile_models import DBUserProfile


@pytest.fixture
def mock_user():
    return {"sub": "test-user-123", "email": "test@example.com"}


@pytest.fixture
def mock_profile():
    return UserProfile(
        id="prof-1",
        user_id="test-user-123",
        name="Alice",
        avatar="data:image/png;base64,samplephoto",
        bio="Hello world",
        timezone="UTC",
        theme_preference="dark",
        preferred_llm_provider="openai",
        default_ai_model="gpt-4o",
        notification_preferences=NotificationPreferences(email=True, in_app=True),
    )


def test_get_profile_api(mock_user, mock_profile):
    mock_service = MagicMock()
    mock_service.get_profile.return_value = mock_profile

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_profile_service] = lambda: mock_service

    client = TestClient(app)
    response = client.get("/api/v1/profile")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test-user-123"
    assert data["name"] == "Alice"
    assert data["avatar"] == "data:image/png;base64,samplephoto"

    app.dependency_overrides.clear()


def test_update_profile_api_clear_avatar(mock_user, mock_profile):
    updated_profile = UserProfile(
        id="prof-1",
        user_id="test-user-123",
        name="Alice",
        avatar=None,
        bio="Hello world",
        timezone="UTC",
        theme_preference="dark",
        preferred_llm_provider="openai",
        default_ai_model="gpt-4o",
        notification_preferences=NotificationPreferences(email=True, in_app=True),
    )
    mock_service = MagicMock()
    mock_service.update_profile.return_value = updated_profile

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_profile_service] = lambda: mock_service

    client = TestClient(app)
    response = client.put("/api/v1/profile", json={"avatar": None})

    assert response.status_code == 200
    data = response.json()
    assert data["avatar"] is None
    mock_service.update_profile.assert_called_once()

    app.dependency_overrides.clear()


def test_delete_avatar_api(mock_user, mock_profile):
    cleared_profile = UserProfile(
        id="prof-1",
        user_id="test-user-123",
        name="Alice",
        avatar=None,
        bio="Hello world",
        timezone="UTC",
        theme_preference="dark",
        preferred_llm_provider="openai",
        default_ai_model="gpt-4o",
        notification_preferences=NotificationPreferences(email=True, in_app=True),
    )
    mock_service = MagicMock()
    mock_service.remove_avatar.return_value = cleared_profile

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_profile_service] = lambda: mock_service

    client = TestClient(app)
    response = client.delete("/api/v1/profile/avatar")

    assert response.status_code == 200
    data = response.json()
    assert data["avatar"] is None
    mock_service.remove_avatar.assert_called_once_with("test-user-123")

    app.dependency_overrides.clear()


def test_user_profile_service_unit():
    mock_db = MagicMock()
    existing_db_profile = DBUserProfile(
        id="prof-1",
        user_id="user-xyz",
        name="Bob",
        avatar="data:image/png;base64,bobphoto",
        bio="Developer",
        timezone="UTC",
        theme_preference="light",
        preferred_llm_provider="openai",
        default_ai_model="gpt-4o",
        notification_preferences={"email": True, "in_app": True}
    )
    mock_db.query.return_value.filter.return_value.first.return_value = existing_db_profile

    service = UserProfileService(mock_db)

    # 1. Test remove_avatar
    res = service.remove_avatar("user-xyz")
    assert res.avatar is None
    assert existing_db_profile.avatar is None
    assert existing_db_profile.name == "Bob"  # other fields untouched
    mock_db.commit.assert_called()

    # 2. Test update_profile explicitly setting avatar to None
    from src.domain.entities.user_profile import UserProfileUpdate
    existing_db_profile.avatar = "https://example.com/newphoto.jpg"
    update_data = UserProfileUpdate(avatar=None)
    res2 = service.update_profile("user-xyz", update_data)
    assert res2.avatar is None
    assert existing_db_profile.avatar is None
    assert existing_db_profile.name == "Bob"
