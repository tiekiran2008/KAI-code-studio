"""
Repository Ingestion & Dynamic RAG Indexing Service
===================================================
Coordinates the full lifecycle of live repository onboarding:
1. Validation & Sandboxed Cloning / Path Resolution
2. File Discovery & Security Filtering (FileFilter)
3. AST-Aware & Structural Chunking (CodeChunker)
4. Vector Embedding & Qdrant Upsert (IndexManager / SentenceTransformer)
5. Repository-Scoped Storage & Clean Re-Indexing
6. Real-time In-Flight Progress & State Management
"""
import os
import shutil
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from src.core.config import settings
from src.core.logger import logger
from src.domain.entities.repository import IndexingStatus
from src.infrastructure.filesystem.file_filter import FileFilter
from src.infrastructure.parsing.code_chunker import CodeChunker
from src.application.services.index_manager import IndexManager
from src.infrastructure.repositories.repository_repository import RepositoryRepository


class RepositoryIndexProgress(BaseModel):
    repository_id: str
    status: str = "pending"
    stage: str = "initialized"
    progress: float = 0.0
    files_discovered: int = 0
    files_processed: int = 0
    chunks_created: int = 0
    error: Optional[str] = None
    started_at: datetime = datetime.now(timezone.utc)
    completed_at: Optional[datetime] = None


# Global thread-safe progress store keyed by repository_id
_GLOBAL_PROGRESS_STORE: Dict[str, RepositoryIndexProgress] = {}


class RepositoryIngestionService:
    """Service that orchestrates repository cloning, parsing, chunking, and vector indexing."""

    def __init__(
        self,
        index_manager: IndexManager,
        repo_repository: RepositoryRepository,
        code_chunker: Optional[CodeChunker] = None,
        session_factory: Optional[Any] = None,
    ):
        self.index_manager = index_manager
        self.repo_repository = repo_repository
        self.code_chunker = code_chunker or CodeChunker()
        self.session_factory = session_factory
        self._progress_store: Dict[str, RepositoryIndexProgress] = _GLOBAL_PROGRESS_STORE

    def get_progress(self, repo_id: str) -> RepositoryIndexProgress:
        """Get the current or historical indexing progress for a repository."""
        if repo_id in self._progress_store:
            return self._progress_store[repo_id]

        # If not in memory, check database status
        db_repo = self.repo_repository.get_by_id(repo_id)
        if db_repo:
            status = db_repo.indexing_status or "pending"
            progress = 100.0 if status == "indexed" else 0.0
            return RepositoryIndexProgress(
                repository_id=repo_id,
                status=status,
                stage="completed" if status == "indexed" else status,
                progress=progress,
                chunks_created=db_repo.chunks_count or 0,
                error=getattr(db_repo, "indexing_error", None),
            )

        return RepositoryIndexProgress(
            repository_id=repo_id,
            status="unknown",
            stage="not_found",
            error="Repository not found",
        )

    def _update_progress(
        self,
        repo_id: str,
        status: str,
        stage: str,
        progress: float,
        files_discovered: int = 0,
        files_processed: int = 0,
        chunks_created: int = 0,
        error: Optional[str] = None,
    ):
        prog = self._progress_store.get(repo_id)
        if not prog:
            prog = RepositoryIndexProgress(repository_id=repo_id)
            self._progress_store[repo_id] = prog

        prog.status = status
        prog.stage = stage
        prog.progress = round(progress, 1)
        if files_discovered:
            prog.files_discovered = files_discovered
        if files_processed:
            prog.files_processed = files_processed
        if chunks_created:
            prog.chunks_created = chunks_created
        if error:
            prog.error = error
        if status in ("indexed", "completed", "failed"):
            prog.completed_at = datetime.now(timezone.utc)

    def _get_workspace_path(self, repo_id: str) -> Path:
        """Return the sandboxed target path for this repository under WORKSPACE_ROOT."""
        base_dir = Path(settings.WORKSPACE_ROOT).resolve()
        base_dir.mkdir(parents=True, exist_ok=True)
        repo_dir = base_dir / "repos" / repo_id
        return repo_dir

    def _clone_or_prepare_repo(
        self,
        repo_id: str,
        url: str,
        provider: str,
        token: Optional[str] = None,
        default_branch: str = "main",
    ) -> Path:
        """
        Clones a remote Git repository or validates a local repository path.
        Enforces strict argument safety with zero shell interpretation.
        """
        # 1. Local Directory handling
        if provider == "local" or url.startswith("local://") or os.path.isdir(url):
            local_path = Path(url.replace("local://", "")).resolve()
            if not local_path.exists() or not local_path.is_dir():
                raise ValueError(f"Local repository directory does not exist: {local_path}")
            return local_path

        # 2. Remote Git URL handling
        dest_dir = self._get_workspace_path(repo_id)
        dest_dir.parent.mkdir(parents=True, exist_ok=True)

        # Build safe clone URL (inject token if provided for private repos)
        clone_target_url = url
        if token and token.strip():
            # Support https://<token>@github.com/...
            if url.startswith("https://"):
                clone_target_url = url.replace("https://", f"https://oauth2:{token.strip()}@")

        # Clean existing directory if present to allow fresh clone
        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)

        cmd = [
            "git",
            "clone",
            "--depth", "1",
            "--single-branch",
            "--branch", default_branch,
            clone_target_url,
            str(dest_dir),
        ]

        try:
            # Execute with timeout, no shell=True
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if result.returncode != 0:
                # If branch clone failed, clean directory and try default branch without --branch flag
                if dest_dir.exists():
                    shutil.rmtree(dest_dir, ignore_errors=True)
                fallback_cmd = ["git", "clone", "--depth", "1", clone_target_url, str(dest_dir)]
                fallback_res = subprocess.run(
                    fallback_cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                if fallback_res.returncode != 0:
                    # Sanitize error to prevent leaking token
                    sanitized_err = fallback_res.stderr.replace(token or "", "******") if token else fallback_res.stderr
                    raise RuntimeError(f"Git clone failed: {sanitized_err.strip()}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Git clone timed out after 120 seconds")

        return dest_dir

    def _create_session(self):
        """Create a dedicated Session instance for background task processing."""
        if self.session_factory is None:
            return None
        try:
            res = self.session_factory
            if callable(res):
                res = res()
            if callable(res) and not hasattr(res, "query"):
                res = res()
            return res
        except Exception as e:
            logger.warning("session_creation_failed_in_ingestion", error=str(e))
            return None

    def ingest_repository(
        self,
        repo_id: str,
        user_id: str,
        commit_hash: str = "HEAD",
    ) -> int:
        """
        Execute full synchronous / background ingestion of a repository:
        Clones -> Scans -> Chunks -> Embeds -> Upserts -> Updates DB.
        """
        start_time = time.perf_counter()
        session = self._create_session()
        if session is not None:
            repo_repo = RepositoryRepository(session)
            idx_mgr = IndexManager(self.index_manager.embedding_service, self.index_manager.vector_db, session)
        else:
            repo_repo = self.repo_repository
            idx_mgr = self.index_manager

        self._update_progress(repo_id, status="indexing", stage="cloning", progress=5.0)

        db_repo = repo_repo.get_by_id(repo_id)
        if not db_repo:
            err = "Repository not found in DB"
            self._update_progress(repo_id, status="failed", stage="failed", progress=0.0, error=err)
            if session:
                session.close()
            return 0

        # Update DB status to INDEXING
        repo_repo.set_indexing_status(repo_id, status=IndexingStatus.INDEXING.value, chunks_count=0)

        try:
            # Stage 1: Clone / Prepare repository
            logger.info("repository_ingestion_start", repo_id=repo_id, url=db_repo.url, branch=db_repo.default_branch or "main")
            repo_path = self._clone_or_prepare_repo(
                repo_id=repo_id,
                url=db_repo.url,
                provider=db_repo.provider or "github",
                token=db_repo.git_access_token_encrypted,
                default_branch=db_repo.default_branch or "main",
            )

            # Stage 2: Discover and filter source files
            self._update_progress(repo_id, status="indexing", stage="scanning", progress=25.0)
            discovered_files: List[Path] = []
            for root, dirs, files in os.walk(repo_path):
                # Prune forbidden directories in-place
                dirs[:] = [d for d in dirs if not FileFilter.should_ignore_dir(d)]

                for file_name in files:
                    full_file_path = Path(root) / file_name
                    rel_to_repo = full_file_path.relative_to(repo_path)
                    try:
                        size = full_file_path.stat().st_size
                    except OSError:
                        size = 0

                    is_valid, _ = FileFilter.is_valid_file(str(rel_to_repo), size)
                    if is_valid:
                        discovered_files.append(full_file_path)

            total_files = len(discovered_files)
            self._update_progress(
                repo_id,
                status="indexing",
                stage="chunking",
                progress=40.0,
                files_discovered=total_files,
            )

            # Stage 3: Parse and generate chunks
            all_chunks = []
            for idx, file_path in enumerate(discovered_files):
                try:
                    rel_str = str(file_path.relative_to(repo_path)).replace("\\", "/")
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    file_chunks = self.code_chunker.chunk_file(
                        repo_id=repo_id,
                        file_path=rel_str,
                        content=content,
                        commit_hash=commit_hash,
                    )
                    all_chunks.extend(file_chunks)
                except Exception as e:
                    logger.warning("Failed to chunk file", file=str(file_path), error=str(e))

                if idx % 20 == 0 or idx == total_files - 1:
                    chunking_progress = 40.0 + (30.0 * ((idx + 1) / max(total_files, 1)))
                    self._update_progress(
                        repo_id,
                        status="indexing",
                        stage="chunking",
                        progress=chunking_progress,
                        files_processed=idx + 1,
                        chunks_created=len(all_chunks),
                    )

            # Stage 4: Embed & Upsert into Qdrant
            self._update_progress(
                repo_id,
                status="indexing",
                stage="embedding",
                progress=70.0,
                chunks_created=len(all_chunks),
            )

            def on_progress(done_chunks: int, total_c: int):
                pct = 70.0 + (25.0 * (done_chunks / max(total_c, 1)))
                self._update_progress(
                    repo_id,
                    status="indexing",
                    stage="indexing",
                    progress=pct,
                    chunks_created=total_c,
                )

            total_indexed = idx_mgr.index_full_repository(
                repo_id=repo_id,
                commit_hash=commit_hash,
                chunks=all_chunks,
                progress_callback=on_progress,
            )

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            # Stage 5: Mark Completed in PostgreSQL (valid only if vectors exist)
            final_status = IndexingStatus.INDEXED.value if total_indexed > 0 else IndexingStatus.FAILED.value
            final_error = None if total_indexed > 0 else "Repository indexing produced 0 chunks"

            if final_status == IndexingStatus.INDEXED.value:
                repo_repo.set_indexing_status(
                    repo_id=repo_id,
                    status=final_status,
                    chunks_count=total_indexed,
                )
            else:
                repo_repo.set_indexing_status(
                    repo_id=repo_id,
                    status=final_status,
                    chunks_count=0,
                    error=final_error,
                )

            self._update_progress(
                repo_id,
                status=final_status,
                stage="completed" if total_indexed > 0 else "failed",
                progress=100.0 if total_indexed > 0 else 0.0,
                files_processed=total_files,
                chunks_created=total_indexed,
                error=final_error,
            )
            logger.info(
                "repository_ingestion_success",
                repository_id=repo_id,
                stage="completed",
                duration_ms=duration_ms,
                files_discovered=total_files,
                chunks_created=total_indexed,
                embeddings_created=total_indexed,
                qdrant_points_written=total_indexed,
                final_status=final_status,
            )
            return total_indexed

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            err_msg = str(exc)
            logger.error(
                "repository_ingestion_failed",
                repository_id=repo_id,
                stage="failed",
                duration_ms=duration_ms,
                final_status=IndexingStatus.FAILED.value,
                safe_error_message=err_msg[:300],
            )
            repo_repo.set_indexing_status(
                repo_id=repo_id,
                status=IndexingStatus.FAILED.value,
                chunks_count=0,
                error=err_msg,
            )
            self._update_progress(
                repo_id,
                status="failed",
                stage="failed",
                progress=0.0,
                error=err_msg,
            )
            return 0
        finally:
            if session is not None:
                session.close()
