from typing import List, Optional
from src.domain.entities.project import Project, ProjectCreate, ProjectUpdate, ProjectDashboard, ProjectStatus
from src.infrastructure.repositories.project_repository import ProjectRepository
from src.application.services.repository_service import RepositoryService


class ProjectService:
    def __init__(self, project_repo: ProjectRepository, repo_service: RepositoryService):
        self.project_repo = project_repo
        self.repo_service = repo_service

    def _to_entity(self, db_project, user_id: str) -> Project:
        repos = [self.repo_service._to_entity(r) for r in (db_project.repositories or [])]
        return Project(
            id=db_project.id,
            user_id=db_project.user_id,
            workspace_id=db_project.workspace_id,
            name=db_project.name,
            description=db_project.description,
            status=ProjectStatus(db_project.status or "active"),
            repositories=repos,
            created_at=db_project.created_at,
            updated_at=db_project.updated_at,
        )

    def create_project(self, user_id: str, data: ProjectCreate) -> Project:
        db_project = self.project_repo.create(
            user_id=user_id,
            data={"name": data.name, "description": data.description, "workspace_id": data.workspace_id},
            repository_ids=data.repository_ids,
        )
        return self._to_entity(db_project, user_id)

    def get_project(self, user_id: str, project_id: str) -> Optional[Project]:
        db_project = self.project_repo.get_by_id(project_id)
        if not db_project or db_project.user_id != user_id:
            return None
        return self._to_entity(db_project, user_id)

    def list_projects(self, user_id: str, workspace_id: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[Project]:
        db_projects = self.project_repo.list_by_user(user_id, workspace_id, skip, limit)
        return [self._to_entity(p, user_id) for p in db_projects]

    def update_project(self, user_id: str, project_id: str, data: ProjectUpdate) -> Optional[Project]:
        db_project = self.project_repo.get_by_id(project_id)
        if not db_project or db_project.user_id != user_id:
            return None
        updated = self.project_repo.update(project_id, data.model_dump(exclude_unset=True))
        return self._to_entity(updated, user_id) if updated else None

    def archive_project(self, user_id: str, project_id: str) -> Optional[Project]:
        db_project = self.project_repo.get_by_id(project_id)
        if not db_project or db_project.user_id != user_id:
            return None
        updated = self.project_repo.update(project_id, {"status": ProjectStatus.ARCHIVED.value})
        return self._to_entity(updated, user_id) if updated else None

    def delete_project(self, user_id: str, project_id: str) -> bool:
        db_project = self.project_repo.get_by_id(project_id)
        if not db_project or db_project.user_id != user_id:
            return False
        return self.project_repo.delete(project_id)

    def link_repository(self, user_id: str, project_id: str, repo_id: str) -> Optional[Project]:
        db_project = self.project_repo.get_by_id(project_id)
        if not db_project or db_project.user_id != user_id:
            return None

        # Ensure user owns repo as well
        repo = self.repo_service.get_repository(user_id, repo_id)
        if not repo:
            return None

        self.project_repo.link_repository(project_id, repo_id)
        return self.get_project(user_id, project_id)

    def unlink_repository(self, user_id: str, project_id: str, repo_id: str) -> Optional[Project]:
        db_project = self.project_repo.get_by_id(project_id)
        if not db_project or db_project.user_id != user_id:
            return None

        self.project_repo.unlink_repository(project_id, repo_id)
        return self.get_project(user_id, project_id)

    def get_dashboard(self, user_id: str, project_id: str) -> Optional[ProjectDashboard]:
        project = self.get_project(user_id, project_id)
        if not project:
            return None

        total_repos = len(project.repositories)
        indexed = sum(1 for r in project.repositories if r.indexing_status == "indexed")
        failed = sum(1 for r in project.repositories if r.indexing_status == "failed")
        chunks = sum(r.chunks_count for r in project.repositories)

        languages = list(set([
            stat.language for r in project.repositories for stat in r.language_stats if stat.language
        ]))

        return ProjectDashboard(
            project=project,
            total_repositories=total_repos,
            indexed_repositories=indexed,
            failed_repositories=failed,
            total_chunks=chunks,
            languages=languages,
        )
