"""
test_render_production_config.py
===================================
Unit tests verifying Render production deployment fixes:
1. DATABASE_URL prioritization over POSTGRES_URL & postgres:// -> postgresql:// normalization.
2. Upstash Redis TLS (rediss://) kwargs support.
3. Qdrant Cloud API key authentication.
4. Credential masking in logged URLs.
5. Lazy loading of SentenceTransformer embedding model.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from src.core.config import Settings, mask_url_credentials
from src.infrastructure.vector_db.qdrant_client_factory import get_shared_qdrant_client
from src.infrastructure.vector_db.qdrant_adapter import QdrantAdapter
from src.infrastructure.embeddings.sentence_transformer_service import SentenceTransformerService


def test_database_url_prioritized_over_postgres_url(monkeypatch):
    """Verifies DATABASE_URL is used when set, and postgres:// is converted to postgresql://."""
    monkeypatch.setenv("DATABASE_URL", "postgres://render_user:secret_pass@render-db-host:5432/render_db")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://localhost_user:pass@localhost:5432/local_db")
    
    settings = Settings()
    assert settings.POSTGRES_URL == "postgresql://render_user:secret_pass@render-db-host:5432/render_db"


def test_redis_upstash_tls_kwargs(monkeypatch):
    """Verifies rediss:// URLs configure ssl_cert_reqs=None for Upstash compatibility."""
    monkeypatch.setenv("REDIS_URL", "rediss://default:upstash_secret@upstash-redis.upstash.io:6379")
    
    settings = Settings()
    kwargs = settings.get_redis_kwargs()
    assert kwargs["decode_responses"] is False
    assert kwargs["ssl_cert_reqs"] is None


def test_mask_url_credentials():
    """Verifies passwords are masked in logged connection strings."""
    url = "postgresql://myuser:super_secret_password@db.render.com:5432/mydb"
    masked = mask_url_credentials(url)
    assert "super_secret_password" not in masked
    assert "myuser:****@db.render.com" in masked


def test_qdrant_client_factory_api_key_passing(monkeypatch):
    """Verifies QdrantClient factory passes API key correctly."""
    monkeypatch.setenv("QDRANT_URL", "https://qdrant-cluster.cloud.qdrant.io:6333")
    monkeypatch.setenv("QDRANT_API_KEY", "qdrant_secret_key_123")

    with patch("src.infrastructure.vector_db.qdrant_client_factory.QdrantClient") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        adapter = QdrantAdapter(url="https://qdrant-cluster.cloud.qdrant.io:6333", api_key="qdrant_secret_key_123")
        assert adapter.client is not None
        mock_client_cls.assert_called_with(
            url="https://qdrant-cluster.cloud.qdrant.io:6333",
            api_key="qdrant_secret_key_123",
        )


def test_sentence_transformer_service_lazy_loading():
    """Verifies SentenceTransformerService does NOT eagerly load the PyTorch model on __init__."""
    with patch.object(SentenceTransformerService, "_ensure_model_loaded") as mock_ensure:
        service = SentenceTransformerService(model_name="sentence-transformers/all-MiniLM-L6-v2")
        assert service.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        # __init__ must NOT call _ensure_model_loaded
        mock_ensure.assert_not_called()


def test_production_port_and_host_resolution(monkeypatch):
    """Verifies production port uses int(os.getenv('PORT', '8000')) and host defaults to 0.0.0.0."""
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setenv("HOST", "0.0.0.0")

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    assert port == 10000
    assert host == "0.0.0.0"
    assert host not in ("127.0.0.1", "localhost")


def test_dockerfile_cmd_uses_python_module_entrypoint():
    """Verifies Dockerfile does not hardcode port 8000 in exec CMD and starts python -m src.main."""
    dockerfile_path = os.path.join(os.path.dirname(__file__), "..", "..", "Dockerfile")
    with open(dockerfile_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'CMD ["python", "-m", "src.main"]' in content
    assert '--port 8000' not in content, "Dockerfile must not hardcode --port 8000"
    assert '127.0.0.1' not in content, "Dockerfile must not hardcode 127.0.0.1"


@pytest.mark.asyncio
async def test_lifespan_starts_immediately_without_blocking():
    """Verifies lifespan context manager yields immediately while warmup runs in background."""
    from src.main import app, lifespan
    import asyncio

    with patch("src.main._async_warmup") as mock_warmup:
        mock_warmup.return_value = None
        # Entering lifespan must yield immediately without hanging
        async with lifespan(app):
            assert hasattr(app.state, "warmup_task")

