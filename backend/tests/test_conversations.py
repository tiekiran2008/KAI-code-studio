"""
Tests for Conversation Persistence and API Endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.infrastructure.persistence.base import Base
from src.infrastructure.repositories.conversation_repository import ConversationRepository
from src.application.services.conversation_service import ConversationService
from src.interfaces.api.dependencies import get_current_user, get_db_session


# Setup in-memory SQLite for testing repository & service
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_conversation_repository_crud(db_session):
    repo = ConversationRepository(db_session)
    user_id = "test-user-123"

    # 1. Create Session
    session = repo.create_session(
        user_id=user_id,
        title="Test Chat",
        repository_id="repo-abc",
        session_id="session-1",
    )
    assert session.id == "session-1"
    assert session.user_id == user_id
    assert session.title == "Test Chat"

    # 2. Add Message
    msg1 = repo.add_message(
        user_id=user_id,
        session_id="session-1",
        role="user",
        content="Hello AI",
        msg_id="msg-1",
    )
    assert msg1.id == "msg-1"
    assert msg1.content == "Hello AI"
    assert msg1.role == "user"

    msg2 = repo.add_message(
        user_id=user_id,
        session_id="session-1",
        role="assistant",
        content="Hello! How can I help?",
        agent_traces=[{"agent": "supervisor", "action": "respond"}],
        citations=[{"file_path": "main.py", "start_line": 1, "end_line": 10}],
        tool_calls=[],
        msg_id="msg-2",
    )
    assert msg2.id == "msg-2"
    assert len(msg2.agent_traces_json) == 1
    assert len(msg2.citations_json) == 1

    # 3. Get Session
    fetched = repo.get_session(user_id=user_id, session_id="session-1")
    assert fetched is not None
    assert len(fetched.messages) == 2
    assert fetched.messages[0].content == "Hello AI"
    assert fetched.messages[1].content == "Hello! How can I help?"

    # 4. User Isolation: Another user cannot access session
    other_fetched = repo.get_session(user_id="other-user", session_id="session-1")
    assert other_fetched is None

    # 5. List Sessions
    sessions = repo.list_sessions(user_id=user_id)
    assert len(sessions) == 1
    assert sessions[0].id == "session-1"

    # 6. Clear Messages
    repo.clear_session_messages(user_id=user_id, session_id="session-1")
    refetched = repo.get_session(user_id=user_id, session_id="session-1")
    assert len(refetched.messages) == 0

    # 7. Delete Session
    deleted = repo.delete_session(user_id=user_id, session_id="session-1")
    assert deleted is True
    assert repo.get_session(user_id=user_id, session_id="session-1") is None


from sqlalchemy.pool import StaticPool

def test_conversation_api_endpoints():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    client = TestClient(app)
    user_id = "test-api-user"

    # Mock dependencies
    app.dependency_overrides[get_current_user] = lambda: {"sub": user_id, "email": "test@example.com"}
    app.dependency_overrides[get_db_session] = override_get_db

    try:
        # Create session via API
        create_res = client.post(
            "/api/v1/conversations",
            json={"id": "test-sess-api", "title": "API Test Session", "repository_id": "repo-1"},
        )
        assert create_res.status_code in (200, 201), create_res.text
        data = create_res.json()
        assert data["id"] == "test-sess-api"
        assert data["title"] == "API Test Session"

        # Add message
        msg_res = client.post(
            "/api/v1/conversations/test-sess-api/messages",
            json={
                "id": "msg-api-1",
                "role": "user",
                "content": "What does this repo do?",
            },
        )
        assert msg_res.status_code in (200, 201), msg_res.text
        msg_data = msg_res.json()
        assert msg_data["content"] == "What does this repo do?"

        # Add AI response
        ai_res = client.post(
            "/api/v1/conversations/test-sess-api/messages",
            json={
                "id": "msg-api-2",
                "role": "assistant",
                "content": "This repo contains a full software engineering agent platform.",
                "agentTraces": [{"agent": "planner", "action": "plan"}],
                "citations": [{"file_path": "README.md", "start_line": 1, "end_line": 5}],
            },
        )
        assert ai_res.status_code in (200, 201), ai_res.text

        # Get session
        get_res = client.get("/api/v1/conversations/test-sess-api")
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert len(get_data["messages"]) == 2

        # List sessions
        list_res = client.get("/api/v1/conversations")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert any(s["id"] == "test-sess-api" for s in list_data)

        # Delete session
        del_res = client.delete("/api/v1/conversations/test-sess-api")
        assert del_res.status_code == 204

    finally:
        app.dependency_overrides.pop(get_current_user, None)
