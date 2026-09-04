"""
File Filtering & Sanitization
==============================
Filters repository files during indexing to exclude:
- VCS & dependency directories (.git, node_modules, .venv, venv, __pycache__, etc.)
- Secret, credential, and environment files (.env, *.pem, *.key, *.id_rsa, *.sqlite, *.db)
- Binary, media, and compiled artifacts (.png, .jpg, .ico, .exe, .dll, .so, .zip, .tar, .pdf, .woff, etc.)
- Large files exceeding size limits (default 1MB)
- Path traversal and null byte anomalies
"""
import os
from pathlib import Path
from typing import Set, Tuple, Optional


class FileFilter:
    """Hardened file filter for source repository discovery and ingestion."""

    # Maximum file size in bytes for indexing (1 MB)
    MAX_FILE_SIZE_BYTES: int = 1_048_576

    # Directories that must NEVER be traversed or indexed
    FORBIDDEN_DIR_NAMES: Set[str] = {
        ".git",
        ".svn",
        ".hg",
        "node_modules",
        "bower_components",
        "vendor",
        "dist",
        "build",
        "out",
        "target",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "coverage",
        ".nyc_output",
        ".next",
        ".nuxt",
        ".cache",
        ".idea",
        ".vscode",
        ".gradle",
        "bin",
        "obj",
        "qdrant_db_local",
    }

    # Explicit file names to forbid (e.g. env files, keys, databases)
    FORBIDDEN_EXACT_FILENAMES: Set[str] = {
        ".env",
        ".env.local",
        ".env.development",
        ".env.production",
        ".env.test",
        ".env.staging",
        "id_rsa",
        "id_dsa",
        "id_ed25519",
        "id_ecdsa",
    }

    # File extensions for binary, archive, or non-indexable content
    FORBIDDEN_EXTENSIONS: Set[str] = {
        # Executables and libraries
        ".exe", ".dll", ".so", ".dylib", ".bin", ".iso", ".msi", ".dmg",
        ".pyc", ".pyo", ".pyd", ".class", ".jar", ".war", ".ear", ".o", ".a",
        # Archives
        ".zip", ".tar", ".gz", ".tgz", ".bz2", ".7z", ".rar", ".xz",
        # Media & assets
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp", ".tiff",
        ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv", ".flac", ".ogg",
        # Fonts
        ".woff", ".woff2", ".ttf", ".eot", ".otf",
        # Documents & binaries
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        # Databases & raw stores
        ".sqlite", ".sqlite3", ".db", ".mdb", ".parquet", ".arrow",
        # Certificates & keys
        ".pem", ".key", ".pkcs12", ".pfx", ".cer", ".crt", ".der",
        # Source maps & lock files (often huge generated JSON)
        ".map",
    }

    # Supported source code language mapping by extension
    SUPPORTED_EXTENSIONS_MAP = {
        ".py": "python",
        ".pyi": "python",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".js": "javascript",
        ".jsx": "jsx",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".md": "markdown",
        ".markdown": "markdown",
        ".rst": "restructuredtext",
        ".txt": "text",
        ".sql": "sql",
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
        ".ps1": "powershell",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".php": "php",
        ".rb": "ruby",
        ".swift": "swift",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".scala": "scala",
        ".r": "r",
        ".dockerfile": "dockerfile",
        "dockerfile": "dockerfile",
    }

    @classmethod
    def should_ignore_dir(cls, dir_name: str) -> bool:
        """Check if a directory should be skipped during repository walk."""
        return dir_name.lower() in cls.FORBIDDEN_DIR_NAMES or dir_name.startswith(".git")

    @classmethod
    def is_valid_file(cls, relative_path: str, file_size_bytes: int = 0) -> Tuple[bool, Optional[str]]:
        """
        Validate whether a file should be indexed.
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, rejection_reason)
        """
        # Normalize slashes
        clean_path = relative_path.replace("\\", "/").strip()
        parts = clean_path.split("/")
        filename = parts[-1]
        lower_name = filename.lower()

        # 1. Null byte check
        if "\x00" in clean_path:
            return False, "Null byte in path"

        # 2. Check forbidden directories in path segments
        for seg in parts[:-1]:
            if seg.lower() in cls.FORBIDDEN_DIR_NAMES:
                return False, f"Inside forbidden directory '{seg}'"

        # 3. Check exact forbidden filenames
        if lower_name in cls.FORBIDDEN_EXACT_FILENAMES or lower_name.startswith(".env."):
            return False, "Sensitive environment or key file"

        # 4. Check forbidden extensions
        _, ext = os.path.splitext(lower_name)
        if ext in cls.FORBIDDEN_EXTENSIONS:
            return False, f"Forbidden file extension '{ext}'"

        # 5. Check file size
        if file_size_bytes > cls.MAX_FILE_SIZE_BYTES:
            return False, f"File size {file_size_bytes} exceeds limit of {cls.MAX_FILE_SIZE_BYTES} bytes"

        return True, None

    @classmethod
    def detect_language(cls, file_path: str) -> str:
        """Detect language based on extension or filename."""
        clean = file_path.replace("\\", "/").lower()
        filename = clean.split("/")[-1]

        if filename in cls.SUPPORTED_EXTENSIONS_MAP:
            return cls.SUPPORTED_EXTENSIONS_MAP[filename]

        _, ext = os.path.splitext(filename)
        return cls.SUPPORTED_EXTENSIONS_MAP.get(ext, "text")
