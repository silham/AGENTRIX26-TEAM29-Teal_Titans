"""Owner: M1. Application settings loaded from environment / .env."""
from functools import lru_cache

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

    # CORS
    frontend_origin: str = "http://localhost:3000"

    # LLMs (free tiers)
    groq_api_key: str = ""
    gemini_api_key: str = ""

    # Storage
    storage_bucket: str = "documents"
    storage_dir: str = "./.storage"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
