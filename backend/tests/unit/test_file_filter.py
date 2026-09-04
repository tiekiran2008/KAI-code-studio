import pytest
from src.infrastructure.filesystem.file_filter import FileFilter


def test_file_filter_forbids_vcs_and_dependency_directories():
    assert FileFilter.should_ignore_dir(".git") is True
    assert FileFilter.should_ignore_dir("node_modules") is True
    assert FileFilter.should_ignore_dir("venv") is True
    assert FileFilter.should_ignore_dir(".venv") is True
    assert FileFilter.should_ignore_dir("__pycache__") is True
    assert FileFilter.should_ignore_dir("dist") is True
    assert FileFilter.should_ignore_dir("build") is True
    assert FileFilter.should_ignore_dir("src") is False
    assert FileFilter.should_ignore_dir("backend") is False


def test_file_filter_forbids_secret_and_env_files():
    valid, reason = FileFilter.is_valid_file(".env")
    assert valid is False
    assert "Sensitive" in reason

    valid, reason = FileFilter.is_valid_file("config/.env.local")
    assert valid is False

    valid, reason = FileFilter.is_valid_file("id_rsa")
    assert valid is False

    valid, reason = FileFilter.is_valid_file("cert.pem")
    assert valid is False

    valid, reason = FileFilter.is_valid_file("database.sqlite")
    assert valid is False


def test_file_filter_forbids_binary_and_media_files():
    valid, reason = FileFilter.is_valid_file("logo.png")
    assert valid is False
    assert "Forbidden file extension" in reason

    valid, reason = FileFilter.is_valid_file("app.exe")
    assert valid is False

    valid, reason = FileFilter.is_valid_file("bundle.zip")
    assert valid is False


def test_file_filter_accepts_valid_source_files():
    valid, _ = FileFilter.is_valid_file("src/main.py", file_size_bytes=1024)
    assert valid is True

    valid, _ = FileFilter.is_valid_file("frontend/src/App.tsx", file_size_bytes=2048)
    assert valid is True

    valid, _ = FileFilter.is_valid_file("README.md", file_size_bytes=500)
    assert valid is True


def test_file_filter_rejects_oversized_files():
    oversized = FileFilter.MAX_FILE_SIZE_BYTES + 100
    valid, reason = FileFilter.is_valid_file("huge_file.py", file_size_bytes=oversized)
    assert valid is False
    assert "exceeds limit" in reason


def test_file_filter_language_detection():
    assert FileFilter.detect_language("src/main.py") == "python"
    assert FileFilter.detect_language("src/component.tsx") == "tsx"
    assert FileFilter.detect_language("src/index.ts") == "typescript"
    assert FileFilter.detect_language("script.js") == "javascript"
    assert FileFilter.detect_language("config.yaml") == "yaml"
    assert FileFilter.detect_language("Dockerfile") == "dockerfile"
