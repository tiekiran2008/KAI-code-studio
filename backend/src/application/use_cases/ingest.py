import os
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from src.domain.models.repository import Repository, SourceFile
from src.infrastructure.vcs.git_client import GitClient
from src.infrastructure.parsing.python_parser import PythonParser
from src.infrastructure.persistence.models import DBRepository, DBSourceFile, DBCodeSymbol

class IngestRepositoryUseCase:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.git_client = GitClient()
        self.parsers = {
            ".py": PythonParser()
        }

    def execute(self, repo_url: str, branch: str = "main", token: Optional[str] = None) -> Repository:
        repo_id = str(uuid.uuid4())
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        
        clone_path = self.git_client.clone_repository(repo_url, token)
        repo_model = Repository(id=repo_id, url=repo_url, name=repo_name, branch=branch)
        
        for root, _, files in os.walk(clone_path):
            if ".git" in root:
                continue
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in self.parsers:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                    except Exception:
                        continue
                        
                    parser = self.parsers[ext]
                    symbols = parser.parse_symbols(content, file_path)
                    imports = parser.extract_imports(content)
                    
                    rel_path = os.path.relpath(file_path, clone_path)
                    source_file = SourceFile(
                        path=rel_path,
                        language=ext.replace(".", ""),
                        content=content,
                        symbols=symbols,
                        imports=imports
                    )
                    repo_model.files.append(source_file)
                    
        self.git_client.cleanup(clone_path)
        self._save_to_db(repo_model)
        return repo_model

    def _save_to_db(self, repo: Repository):
        db_repo = DBRepository(
            id=repo.id,
            url=repo.url,
            name=repo.name,
            branch=repo.branch
        )
        self.db_session.add(db_repo)
        
        for sf in repo.files:
            file_id = str(uuid.uuid4())
            db_sf = DBSourceFile(
                id=file_id,
                repo_id=repo.id,
                path=sf.path,
                language=sf.language
            )
            self.db_session.add(db_sf)
            
            for sym in sf.symbols:
                db_sym = DBCodeSymbol(
                    id=str(uuid.uuid4()),
                    file_id=file_id,
                    name=sym.name,
                    symbol_type=sym.symbol_type,
                    start_line=sym.start_line,
                    end_line=sym.end_line
                )
                self.db_session.add(db_sym)
                
        self.db_session.commit()
