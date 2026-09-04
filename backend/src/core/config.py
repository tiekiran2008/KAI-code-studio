from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---- Application ----
    ENVIRONMENT: str = "development"

    # ---- Database ----
    POSTGRES_URL: str = "postgresql://agent_user:agent_password@localhost:5432/agent_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---- Vector Store ----
    QDRANT_URL: str = "http://localhost:6333"

    # ---- CORS ----
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

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
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/api/v1/integrations/github/callback"
    FRONTEND_URL: str = "http://localhost:3000"


    # ---- LLM Providers ----
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_PROVIDER: str = "gemini"          # "gemini" | "openai"
    GEMINI_MODEL: str = "gemini-2.5-flash"
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

