import os
import shutil
import tempfile
from git import Repo

class GitClient:
    def __init__(self, workspace_root: str = "/tmp/agent_repos"):
        self.workspace_root = workspace_root
        os.makedirs(self.workspace_root, exist_ok=True)
        
    def clone_repository(self, repo_url: str, token: str = None) -> str:
        """Clones a repository to a local temp folder and returns the path."""
        if token and "https://" in repo_url:
            repo_url = repo_url.replace("https://", f"https://oauth2:{token}@")
        
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        dest_path = tempfile.mkdtemp(prefix=f"{repo_name}_", dir=self.workspace_root)
        
        Repo.clone_from(repo_url, dest_path)
        return dest_path

    def cleanup(self, path: str):
        """Removes the cloned repository directory."""
        if os.path.exists(path):
            shutil.rmtree(path)
