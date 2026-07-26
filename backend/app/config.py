import os
from functools import lru_cache


class Settings:
    # --- Postgres ---
    database_url: str = os.getenv("DATABASE_URL", "")

    # --- LLM provider: "claude" or "openai" ---
    llm_provider: str = os.getenv("LLM_PROVIDER", "claude").lower()
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    # --- Embeddings: only OpenAI's embedding endpoint is wired up here,
    # since Anthropic doesn't currently offer a first-party embeddings API.
    # If ANTHROPIC is the LLM provider, embeddings still use OpenAI.
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "1536"))

    # --- Retrieval ---
    top_k: int = int(os.getenv("RAG_TOP_K", "5"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))       # chars
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))  # chars

    # --- CORS (for the deployed Vercel/Netlify frontend) ---
    allowed_origins: list[str] = os.getenv("ALLOWED_ORIGINS", "*").split(",")

    # --- Admin routes (/admin/seed, /admin/ingest, /admin/documents) ---
    # Required header: X-Admin-Key. Set this to something random; these
    # routes can write to your database, so never leave it blank in prod.
    admin_api_key: str = os.getenv("ADMIN_API_KEY", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
