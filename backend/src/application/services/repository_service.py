from datetime import datetime, timezone
from typing import List, Optional, Any
import time

from src.domain.entities.repository import (
    Repository,
    RepositoryCreate,
    RepositoryUpdate,
    RepositoryHealthCheck,
    RepositoryListParams,
    LanguageStat,
    DetectedStack,
    IndexingStatus,
)
from src.infrastructure.repositories.repository_repository import RepositoryRepository
from src.infrastructure.analysis.stack_detector import StackDetector
from src.domain.interfaces.vector_db import IVectorDB


class RepositoryService:
    def __init__(
        self,
        repo_repository: RepositoryRepository,
        detector: Optional[StackDetector] = None,
        ingestion_service: Optional[Any] = None,
        vector_db: Optional[IVectorDB] = None,
    ):
        self.repo_repository = repo_repository
        self.detector = detector or StackDetector()
        self.ingestion_service = ingestion_service
        self.vector_db = vector_db

    def _to_entity(self, db_repo) -> Repository:
        lang_stats = [LanguageStat(**stat) for stat in (db_repo.language_stats_json or [])]
        stack = DetectedStack(**db_repo.detected_stack_json) if db_repo.detected_stack_json else None

        return Repository(
            id=db_repo.id,
            user_id=db_repo.user_id,
            workspace_id=db_repo.workspace_id,
            url=db_repo.url,
            provider=db_repo.provider,
            name=db_repo.name,
            description=db_repo.description,
            owner=db_repo.owner,
            default_branch=db_repo.default_branch or "main",
            current_branch=db_repo.current_branch or db_repo.default_branch or "main",
            branches=db_repo.branches_json or [db_repo.default_branch or "main"],
            repo_size_kb=db_repo.repo_size_kb,
            language_stats=lang_stats,
            detected_stack=stack,
            indexing_status=db_repo.indexing_status or IndexingStatus.PENDING,
            chunks_count=db_repo.chunks_count or 0,
            last_indexed_at=db_repo.last_indexed_at,
            is_private=db_repo.is_private or False,
            stars=db_repo.stars,
            created_at=db_repo.created_at,
            updated_at=db_repo.updated_at,
        )

    def import_repository(self, user_id: str, data: RepositoryCreate) -> Repository:
        # Check duplicate
        existing = self.repo_repository.get_by_user_and_url(user_id, data.url)
        if existing:
            raise ValueError(f"Repository with URL '{data.url}' has already been imported.")

        # Detect provider & owner/name
        provider = data.provider or self.detector.detect_provider(data.url)
        owner, parsed_name = self.detector.extract_owner_and_name(data.url)
        name = data.name or parsed_name

        # Detect AI stack heuristics
        detected_stack = self.detector.detect(data.url, name, data.description)

        # Build primary language stats
        lang_stats = []
        if detected_stack.language:
            lang_stats.append({"language": detected_stack.language, "percentage": 100.0, "bytes": 10000})

        db_data = {
            "workspace_id": data.workspace_id,
            "url": data.url,
            "provider": provider.value if hasattr(provider, "value") else provider,
            "name": name,
            "description": data.description,
            "owner": owner,
            "default_branch": data.default_branch,
            "current_branch": data.default_branch,
            "branches_json": [data.default_branch, "main", "dev"],
            "language_stats_json": lang_stats,
            "detected_stack_json": detected_stack.model_dump(),
            "indexing_status": IndexingStatus.PENDING.value,
            "chunks_count": 0,
            "last_indexed_at": None,
            "git_access_token_encrypted": data.git_access_token,
        }

        db_repo = self.repo_repository.create(user_id, db_data)
        return self._to_entity(db_repo)

    def get_repository(self, user_id: str, repo_id: str) -> Optional[Repository]:
        db_repo = self.repo_repository.get_by_id(repo_id)
        if not db_repo or db_repo.user_id != user_id:
            return None
        return self._to_entity(db_repo)

    def list_repositories(self, user_id: str, params: RepositoryListParams) -> List[Repository]:
        db_repos = self.repo_repository.list_by_user(user_id, params)
        return [self._to_entity(r) for r in db_repos]

    def update_repository(self, user_id: str, repo_id: str, data: RepositoryUpdate) -> Optional[Repository]:
        db_repo = self.repo_repository.get_by_id(repo_id)
        if not db_repo or db_repo.user_id != user_id:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        updated = self.repo_repository.update(repo_id, update_dict)
        return self._to_entity(updated) if updated else None

    def refresh_repository(self, user_id: str, repo_id: str) -> Optional[Repository]:
        db_repo = self.repo_repository.get_by_id(repo_id)
        if not db_repo or db_repo.user_id != user_id:
            return None

        # Re-run stack detector
        stack = self.detector.detect(db_repo.url, db_repo.name, db_repo.description)
        self.repo_repository.update(repo_id, {"detected_stack_json": stack.model_dump()})

        # If ingestion service available, trigger re-indexing
        if self.ingestion_service:
            self.ingestion_service.ingest_repository(repo_id=repo_id, user_id=user_id)
            refreshed = self.repo_repository.get_by_id(repo_id)
            return self._to_entity(refreshed) if refreshed else None

        updated = self.repo_repository.set_indexing_status(
            repo_id, status=IndexingStatus.INDEXED.value, chunks_count=db_repo.chunks_count or 0
        )
        return self._to_entity(updated) if updated else None

    def delete_repository(self, user_id: str, repo_id: str) -> bool:
        db_repo = self.repo_repository.get_by_id(repo_id)
        if not db_repo or db_repo.user_id != user_id:
            return False

        # Clean Qdrant vectors for this repository if vector_db is wired
        if self.vector_db:
            try:
                self.vector_db.delete_by_repo("codebase_chunks", repo_id)
            except Exception:
                pass

        return self.repo_repository.delete(repo_id)

    def switch_branch(self, user_id: str, repo_id: str, branch: str) -> Optional[Repository]:
        db_repo = self.repo_repository.get_by_id(repo_id)
        if not db_repo or db_repo.user_id != user_id:
            return None
        updated = self.repo_repository.switch_branch(repo_id, branch)
        return self._to_entity(updated) if updated else None

    def health_check(self, user_id: str, repo_id: str) -> RepositoryHealthCheck:
        start = time.time()
        db_repo = self.repo_repository.get_by_id(repo_id)
        if not db_repo or db_repo.user_id != user_id:
            return RepositoryHealthCheck(
                repo_id=repo_id,
                is_reachable=False,
                error="Repository not found or unauthorized",
                checked_at=datetime.now(timezone.utc),
            )

        latency = round((time.time() - start) * 1000, 2)
        return RepositoryHealthCheck(
            repo_id=repo_id,
            is_reachable=True,
            latency_ms=latency,
            checked_at=datetime.now(timezone.utc),
        )
