import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
import time

from src.core.config import settings
from src.domain.entities.repository import (
    Repository,
    RepositoryProvider,
    RepositoryCreate,
    RepositoryUpdate,
    RepositoryHealthCheck,
    RepositoryListParams,
    LanguageStat,
    DetectedStack,
    IndexingStatus,
    FileNode,
    FileContentResponse,
)
from src.infrastructure.repositories.repository_repository import RepositoryRepository
from src.infrastructure.analysis.stack_detector import StackDetector
from src.infrastructure.filesystem.path_sandbox import PathSandboxService
from src.infrastructure.filesystem.file_filter import FileFilter
from src.domain.interfaces.vector_db import IVectorDB


def _build_tree_from_paths(repo_id: str, paths: List[str]) -> List[FileNode]:
    """
    Convert a flat sorted list of POSIX relative file paths into a nested FileNode tree.
    Used as a Qdrant-based fallback when the local git clone directory is absent.
    """
    # Build a nested dict: { "segment": { "__files__": [...], "subdir": {...} } }
    root: Dict = {}

    for path in paths:
        parts = path.replace("\\", "/").lstrip("/").split("/")
        node = root
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        file_name = parts[-1]
        node.setdefault("__files__", []).append((file_name, path))

    def dict_to_nodes(d: Dict, depth: int = 0) -> List[FileNode]:
        nodes: List[FileNode] = []
        # Directories first (sorted), then files
        dir_keys = sorted(k for k in d if k != "__files__")
        for key in dir_keys:
            sub = d[key]
            # Derive rel_path by collecting the first file path under this dir
            # We reconstruct relative path from the nested file paths
            child_nodes = dict_to_nodes(sub, depth + 1)
            # Extract rel_path from first child to compute dir path
            first_child_path = _first_path(child_nodes)
            if first_child_path:
                rel_path = "/".join(first_child_path.split("/")[: depth + 1])
            else:
                rel_path = key
            nodes.append(
                FileNode(
                    id=f"dir-{repo_id}-{rel_path}",
                    name=key,
                    path=rel_path,
                    type="directory",
                    children=child_nodes,
                )
            )
        for file_name, full_rel_path in sorted(d.get("__files__", [])):
            lang = FileFilter.detect_language(full_rel_path)
            nodes.append(
                FileNode(
                    id=f"file-{repo_id}-{full_rel_path}",
                    name=file_name,
                    path=full_rel_path,
                    type="file",
                    language=lang,
                )
            )
        return nodes

    def _first_path(nodes: List[FileNode]) -> Optional[str]:
        for n in nodes:
            if n.type == "file":
                return n.path
            if n.children:
                p = _first_path(n.children)
                if p:
                    return p
        return None

    return dict_to_nodes(root)



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

        raw_provider = getattr(db_repo, "provider", None)
        if raw_provider:
            if isinstance(raw_provider, RepositoryProvider):
                provider = raw_provider
            else:
                try:
                    provider = RepositoryProvider(str(raw_provider).lower())
                except ValueError:
                    provider = self.detector.detect_provider(db_repo.url) if getattr(db_repo, "url", None) else RepositoryProvider.GITHUB
        else:
            provider = self.detector.detect_provider(db_repo.url) if getattr(db_repo, "url", None) else RepositoryProvider.GITHUB

        return Repository(
            id=db_repo.id,
            user_id=db_repo.user_id,
            workspace_id=db_repo.workspace_id,
            url=db_repo.url,
            provider=provider,
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

    def _get_repo_dir(self, repo_id: str, db_repo: Any) -> Path:
        """Resolve repository workspace root path on disk."""
        url = getattr(db_repo, "url", "") or ""
        if url.startswith("local://") or (url and os.path.isdir(url)):
            local_path = Path(url.replace("local://", "")).resolve()
            if local_path.exists() and local_path.is_dir():
                return local_path

        base_dir = Path(settings.WORKSPACE_ROOT).resolve()
        return (base_dir / "repos" / repo_id).resolve()

    def get_file_tree(self, user_id: str, repo_id: str) -> List[FileNode]:
        """Fetch sanitized hierarchical file tree for repository.

        Primary: walk the cloned repository on disk (fast, full metadata).
        Fallback: reconstruct from Qdrant chunk metadata when the disk directory
                  is absent (e.g. after an ephemeral Render/serverless restart).
        """
        db_repo = self.repo_repository.get_by_id(repo_id)
        if not db_repo:
            raise ValueError("Repository not found")
        if db_repo.user_id != user_id:
            raise PermissionError("Unauthorized access to repository")

        repo_dir = self._get_repo_dir(repo_id, db_repo)
        if repo_dir.exists() and repo_dir.is_dir():
            # ── Primary path: scan the local clone ──────────────────────────
            def build_tree(current_dir: Path, rel_base: str = "") -> List[FileNode]:
                nodes: List[FileNode] = []
                try:
                    entries = sorted(
                        os.scandir(current_dir),
                        key=lambda e: (not e.is_dir(), e.name.lower()),
                    )
                except Exception:
                    return nodes

                for entry in entries:
                    rel_path = f"{rel_base}/{entry.name}".lstrip("/")
                    if entry.is_dir(follow_symlinks=False):
                        if FileFilter.should_ignore_dir(entry.name):
                            continue
                        children = build_tree(Path(entry.path), rel_path)
                        nodes.append(
                            FileNode(
                                id=f"dir-{repo_id}-{rel_path}",
                                name=entry.name,
                                path=rel_path,
                                type="directory",
                                children=children,
                            )
                        )
                    elif entry.is_file(follow_symlinks=False):
                        try:
                            size = entry.stat().st_size
                        except Exception:
                            size = 0
                        is_valid, _ = FileFilter.is_valid_file(rel_path, size)
                        if not is_valid:
                            continue
                        lang = FileFilter.detect_language(rel_path)
                        nodes.append(
                            FileNode(
                                id=f"file-{repo_id}-{rel_path}",
                                name=entry.name,
                                path=rel_path,
                                type="file",
                                size=size,
                                language=lang,
                            )
                        )
                return nodes

            return build_tree(repo_dir)

        # ── Fallback path: reconstruct tree from Qdrant index ────────────────
        # Used when the ephemeral local clone no longer exists after a restart.
        if self.vector_db is None:
            return []

        try:
            file_paths = self.vector_db.get_indexed_files("codebase_chunks", repo_id)
        except Exception:
            return []

        if not file_paths:
            return []

        return _build_tree_from_paths(repo_id, sorted(file_paths))



    def get_file_content(self, user_id: str, repo_id: str, relative_path: str) -> FileContentResponse:
        """Fetch safe, sandboxed file content for a file in the repository."""
        db_repo = self.repo_repository.get_by_id(repo_id)
        if not db_repo:
            raise ValueError("Repository not found")
        if db_repo.user_id != user_id:
            raise PermissionError("Unauthorized access to repository")

        repo_dir = self._get_repo_dir(repo_id, db_repo)
        if not repo_dir.exists() or not repo_dir.is_dir():
            raise FileNotFoundError("Repository directory not found on disk")

        # Strip leading slashes from requested path
        clean_rel = relative_path.lstrip("/\\")
        if not clean_rel:
            raise ValueError("File path cannot be empty")

        safe_path = PathSandboxService.validate_path(repo_dir, clean_rel, must_be_file=True)
        if not safe_path.exists() or not safe_path.is_file():
            raise FileNotFoundError(f"File not found: {clean_rel}")

        size = safe_path.stat().st_size
        if size > 2 * 1024 * 1024:
            raise ValueError(f"File size ({size} bytes) exceeds maximum viewing limit of 2MB")

        is_valid, reason = FileFilter.is_valid_file(clean_rel, size)
        if not is_valid and reason and "Sensitive" in reason:
            raise PermissionError(f"Access to sensitive file is forbidden: {reason}")

        try:
            content = safe_path.read_text(encoding="utf-8")
            is_binary = False
        except UnicodeDecodeError:
            content = "[Binary file cannot be displayed as text]"
            is_binary = True

        lang = FileFilter.detect_language(clean_rel)
        return FileContentResponse(
            path=clean_rel.replace("\\", "/"),
            name=safe_path.name,
            content=content,
            size=size,
            language=lang,
            is_binary=is_binary,
        )

