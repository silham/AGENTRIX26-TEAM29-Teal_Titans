"""Owner: M1. Application settings loaded from environment / .env."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    app_name: str = "HelpLK AI"
    environment: str = "development"

    # Database — defaults to SQLite so demo works without PostgreSQL.
    # Override with a real Postgres URL in .env for production.
    database_url: str = "sqlite:///./helplk.db"

    # Auth — shared with NextAuth (HS256)
    auth_secret: str = "change-me-shared-with-nextauth"
    jwt_algorithm: str = "HS256"

    # Admin allowlist for the knowledge-base uploader (comma-separated emails).
    # Deliberately a str, not list[str]: pydantic-settings JSON-parses list-typed
    # fields, which chokes on the natural "a@x.lk,b@y.lk" form.
    admin_emails: str = ""

    # CORS
    frontend_origin: str = "http://localhost:3000"

    # LLMs (free tiers)
    groq_api_key: str = ""
    gemini_api_key: str = ""

    # Storage
    storage_bucket: str = "documents"
    storage_dir: str = "./.storage"

    # RAG tuning. rag_min_score is an OVERRIDE: leave it unset and the retriever
    # uses a per-embedding-model default, because Gemini and the local fallback
    # produce incompatible score scales (see llm/embeddings.DEFAULT_MIN_SCORE).
    rag_min_score: float | None = None
    rag_top_k: int = 4
    max_knowledge_upload_mb: int = 20

    @field_validator("database_url")
    @classmethod
    def _normalise_pg_scheme(cls, v: str) -> str:
        """Force psycopg3 for Postgres URLs.

        SQLAlchemy resolves a bare ``postgresql://`` to psycopg2, which this
        project does not ship (requirements pins ``psycopg[binary]``, i.e.
        psycopg3). Normalising here means no teammate's .env can be wrong.
        """
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]

    @property
    def admin_email_set(self) -> set[str]:
        """Lowercased admin emails. A plain property (not cached) so tests can
        monkeypatch ``admin_emails`` and operators can revoke by editing .env."""
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
