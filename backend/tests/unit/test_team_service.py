import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from src.application.services.team_service import TeamService
from src.domain.entities.team import RoleEnum, TeamCreate
from src.infrastructure.persistence.team_models import DBTeam, DBTeamMember

@pytest.fixture
def mock_db_session():
    session = MagicMock()
    return session

@pytest.fixture
def team_service(mock_db_session):
    return TeamService(session=mock_db_session)

def test_create_team(team_service, mock_db_session):
    team_data = TeamCreate(name="Engineering Team", description="Core engineers")
    owner_id = "user_123"
    
    def mock_refresh(obj):
        if isinstance(obj, DBTeam):
            now = datetime.now(timezone.utc)
            obj.created_at = now
            obj.updated_at = now
            obj.members = [DBTeamMember(id="m1", team_id=obj.id, user_id=owner_id, role=RoleEnum.OWNER.value, joined_at=now)]
    mock_db_session.refresh.side_effect = mock_refresh

    team = team_service.create_team(owner_id, team_data)
    
    assert team.name == "Engineering Team"
    assert team.owner_id == owner_id
    assert mock_db_session.add.called
    assert mock_db_session.commit.called

def test_transfer_ownership_requires_owner(team_service, mock_db_session):
    team_id = "team_1"
    owner_id = "user_owner"
    new_owner_id = "user_new"
    
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = DBTeamMember(id="m2", team_id=team_id, user_id="user_hacker", role=RoleEnum.DEVELOPER.value)
    mock_db_session.query.return_value = mock_query

    result = team_service.transfer_ownership("user_hacker", team_id, new_owner_id)
    assert result is None

def test_remove_member(team_service, mock_db_session):
    team_id = "team_1"
    remover_id = "user_admin"
    target_id = "user_dev"

    remover = DBTeamMember(id="m1", team_id=team_id, user_id=remover_id, role=RoleEnum.ADMIN.value)
    target = DBTeamMember(id="m2", team_id=team_id, user_id=target_id, role=RoleEnum.DEVELOPER.value)

    def query_filter_side_effect(*args, **kwargs):
        filter_mock = MagicMock()
        filter_mock.first.side_effect = [remover, target]
        return filter_mock

    mock_db_session.query.return_value.filter.side_effect = query_filter_side_effect

    success = team_service.remove_member(remover_id, team_id, target_id)
    assert success is True
    assert mock_db_session.delete.called
    assert mock_db_session.commit.called
