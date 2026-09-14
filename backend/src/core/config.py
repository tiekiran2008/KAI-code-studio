import json
import os
import re
from typing import Any, Dict, List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def mask_url_credentials(url: str) -> str:
    """Utility to mask username/passwords in connection URLs for safe logging."""
    if not url:
        return ""
    return re.sub(r"://([^:@]+):([^@]+)@", r"://\1:****@", url)


class Settings(BaseSettings):
    # ---- Application ----
    ENVIRONMENT: str = "development"

    # ---- Database ----
    DATABASE_URL: str = ""
    POSTGRES_URL: str = "postgresql://agent_user:agent_password@localhost:5432/agent_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---- Vector Store ----
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""

    @model_validator(mode="after")
    def assemble_effective_urls(self) -> "Settings":
        # Render sets DATABASE_URL; prioritize DATABASE_URL if non-empty, otherwise POSTGRES_URL
        effective_db = (
            os.getenv("DATABASE_URL")
            or self.DATABASE_URL
            or os.getenv("POSTGRES_URL")
            or self.POSTGRES_URL
        )
        if effective_db:
            if effective_db.startswith("postgres://"):
                effective_db = effective_db.replace("postgres://", "postgresql://", 1)
            self.POSTGRES_URL = effective_db

        # Automatically include FRONTEND_URL in CORS_ORIGINS
        frontend_url = os.getenv("FRONTEND_URL") or self.FRONTEND_URL
        if frontend_url:
            for url_part in frontend_url.split(","):
                cleaned = url_part.strip().rstrip("/")
                if cleaned and cleaned not in self.CORS_ORIGINS:
                    self.CORS_ORIGINS.append(cleaned)

        return self

    def get_redis_kwargs(self) -> Dict[str, Any]:
        """Returns redis client kwargs, injecting ssl settings for Upstash/rediss TLS connections."""
        kwargs: Dict[str, Any] = {"decode_responses": False}
        if self.REDIS_URL.startswith("rediss://"):
            kwargs["ssl_cert_reqs"] = None
        return kwargs

    # ---- CORS ----
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:80",
        "http://127.0.0.1:80",
        "http://localhost",
        "http://127.0.0.1",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        origins: List[str] = []
        if isinstance(v, str):
            raw = v.strip()
            if raw.startswith("[") and raw.endswith("]"):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        origins = [str(item).strip().rstrip("/") for item in parsed if item]
                except Exception:
                    pass
            if not origins:
                origins = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
        elif isinstance(v, list):
            origins = [str(item).strip().rstrip("/") for item in v if item]

        # Ensure both localhost:3000 and 127.0.0.1:3000 are present if either is configured
        if "http://localhost:3000" in origins and "http://127.0.0.1:3000" not in origins:
            origins.append("http://127.0.0.1:3000")
        if "http://127.0.0.1:3000" in origins and "http://localhost:3000" not in origins:
            origins.append("http://localhost:3000")
        if "http://localhost:5173" in origins and "http://127.0.0.1:5173" not in origins:
            origins.append("http://127.0.0.1:5173")
        if "http://127.0.0.1:5173" in origins and "http://localhost:5173" not in origins:
            origins.append("http://localhost:5173")

        return list(dict.fromkeys(origins))

    # ---- Authentication ----
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    DEV_AUTH_BYPASS: bool = False
    DEV_AUTH_USER_EMAIL: str = "dev-user@example.com"

    # ---- GitHub OAuth Integration ----
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = "http://127.0.0.1:8000/api/v1/integrations/github/callback"
    FRONTEND_URL: str = "http://127.0.0.1:3000"



    # ---- LLM Providers ----
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_PROVIDER: str = "gemini"          # "gemini" | "openai"
    GEMINI_MODEL: str = "gemini-3.6-flash"
    OPENAI_MODEL: str = "gpt-4o"

    # ---- RAG Pipeline ----
    CONTEXT_WINDOW_TOKENS: int = 12_000   # Max tokens fed to LLM context
    MAX_RETRIEVED_CHUNKS: int = 20        # Raw candidates before re-ranking
    TOP_K_CHUNKS: int = 8                 # Chunks kept after re-ranking
    CONVERSATION_TTL_SECONDS: int = 7_200 # 2-hour session window in Redis
    MIN_CONFIDENCE_THRESHOLD: float = 0.35
    RAG_RESPONSE_CACHE_TTL: int = 300     # 5-min cache for identical queries
    LLM_MAX_TOKENS: int = 2_048           # Max completion tokens per request
    LLM_TEMPERATURE: float = 0.2

    # ---- Multi-Agent System (Phase 6) ----
    AGENT_MAX_RECURSION_LIMIT: int = 25   # Prevents infinite loops in LangGraph
    AGENT_EVALUATION_RETRIES_MAX: int = 2 # Max retries when evaluation confidence is low
    AGENT_CONFIDENCE_THRESHOLD: float = 0.40

    # ---- Intelligent Memory (Phase 7) ----
    MEMORY_ENCRYPTION_KEY: str = ""                   # Fernet key; empty = passthrough mode
    MEMORY_SHORT_TERM_TTL_SECONDS: int = 1_800        # 30 min session window in Redis
    MEMORY_LONG_TERM_TTL_DAYS: int = 90               # 90-day retention for long-term memory
    MEMORY_VECTOR_DIM: int = 384                      # Embedding dimension (all-MiniLM-L6-v2)
    MEMORY_VECTOR_COLLECTION: str = "memories"        # Qdrant collection name
    MEMORY_CONSOLIDATION_INACTIVE_DAYS: int = 90      # Archive threshold
    MEMORY_CONSOLIDATION_BATCH_SIZE: int = 200        # Records per consolidation run
    MEMORY_CONTEXT_TOKEN_BUDGET: int = 2_000          # Max tokens from memory in agent context
    MEMORY_SEARCH_TOP_K: int = 5                      # Default semantic search results
    MEMORY_SEARCH_SCORE_THRESHOLD: float = 0.0        # Min similarity score (0 = no filter)

    # ---- Tool Adapters ----
    WORKSPACE_ROOT: str = "./workspace"               # Local file-system root for tool adapters

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

