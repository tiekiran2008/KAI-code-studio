"""
Integration Tests — PostgreSQL Memory Repository
==============================================
Tests the SQLAlchemy-backed IMemoryRepository against an in-memory SQLite DB.
SQLite is used to keep tests fast and self-contained, but the repository
code is identical to what runs against PostgreSQL.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.persistence.models import Base
from src.infrastructure.memory.postgres_memory_repository import PostgresMemoryRepository
from src.infrastructure.memory.memory_encryptor import FernetMemoryEncryptor
from src.domain.memory.entities import (
    MemoryScore,
    MemoryStatus,
    MemoryType,
    ShortTermMemory,
    LongTermMemory,
    UserPreferences,
)


from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="function")
def sqlite_session_factory():
    # StaticPool forces every connection to reuse the SAME in-memory SQLite
    # connection. This is necessary because PostgresMemoryRepository offloads
    # blocking DB calls to a thread-pool via run_in_executor, and the default
    # per-thread connection would see a fresh (empty) database.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield factory
    Base.metadata.drop_all(bind=engine)


@pytest_asyncio.fixture
async def repo(sqlite_session_factory):
    session = sqlite_session_factory()
    # Use passthrough encryptor for tests
    encryptor = FernetMemoryEncryptor(key=None)
    repository = PostgresMemoryRepository(session, encryptor)
    yield repository
    session.close()


@pytest.mark.asyncio
async def test_save_and_get_by_id(repo):
    mem = ShortTermMemory(
        user_id="user1",
        session_id="sess1",
        content="Test content",
        summary="Test summary",
    )
    
    saved = await repo.save(mem)
    assert saved.id is not None
    assert saved.user_id == "user1"
    
    fetched = await repo.get_by_id(saved.id, "user1")
    assert fetched is not None
    assert fetched.content == "Test content"
    assert isinstance(fetched, ShortTermMemory)


@pytest.mark.asyncio
async def test_get_by_id_enforces_user_isolation(repo):
    mem = ShortTermMemory(user_id="user1", content="Secure data")
    saved = await repo.save(mem)
    
    with pytest.raises(PermissionError):
        await repo.get_by_id(saved.id, "user2")


@pytest.mark.asyncio
async def test_update_increments_version(repo):
    mem = ShortTermMemory(user_id="user1", content="V1")
    saved = await repo.save(mem)
    
    saved.content = "V2"
    saved.increment_version()
    
    updated = await repo.update(saved)
    assert updated.content == "V2"
    assert updated.version == 2


@pytest.mark.asyncio
async def test_update_optimistic_concurrency_conflict(repo):
    mem = ShortTermMemory(user_id="user1", content="V1")
    saved = await repo.save(mem)
    
    # Simulate another writer bumping the version in the DB
    saved.content = "V2"
    saved.increment_version()
    await repo.update(saved)
    
    # Try writing with a stale version
    stale = await repo.get_by_id(saved.id, "user1")
    stale.version = 1  # Force stale
    stale.increment_version() # Now it's 2, but DB is at 2 so it expects 1->2 not 2->3 or mismatch
    
    with pytest.raises(ValueError, match="Concurrent modification conflict"):
        await repo.update(stale)


@pytest.mark.asyncio
async def test_soft_delete(repo):
    mem = ShortTermMemory(user_id="user1", content="Sensitive")
    saved = await repo.save(mem)
    
    await repo.soft_delete(saved.id, "user1")
    
    fetched = await repo.get_by_id(saved.id, "user1")
    assert fetched.status == MemoryStatus.DELETED
    assert fetched.content == "[GDPR ERASED]"


@pytest.mark.asyncio
async def test_hard_delete_all_for_user(repo):
    await repo.save(ShortTermMemory(user_id="user1", content="A"))
    await repo.save(LongTermMemory(user_id="user1", content="B"))
    await repo.save(ShortTermMemory(user_id="user2", content="C"))
    
    count = await repo.hard_delete_all_for_user("user1")
    assert count == 2
    
    remains_user2 = await repo.list_by_user("user2")
    assert len(remains_user2) == 1


@pytest.mark.asyncio
async def test_get_expired(repo):
    mem1 = ShortTermMemory(user_id="u", expires_at=datetime.utcnow() - timedelta(minutes=10))
    mem2 = ShortTermMemory(user_id="u", expires_at=datetime.utcnow() + timedelta(minutes=10))
    await repo.save(mem1)
    await repo.save(mem2)
    
    expired = await repo.get_expired()
    assert len(expired) == 1
    assert expired[0].id == mem1.id


@pytest.mark.asyncio
async def test_update_score(repo):
    mem = ShortTermMemory(user_id="u")
    saved = await repo.save(mem)
    
    await repo.update_score(saved.id, {"access_count": 5, "decay_factor": 0.5})
    
    fetched = await repo.get_by_id(saved.id, "u")
    assert fetched.score.access_count == 5
    assert fetched.score.decay_factor == 0.5
