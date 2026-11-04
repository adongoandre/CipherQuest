"""Application settings loaded from environment variables and `.env` files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent

# SQLite is a local development/test convenience only. The product target is
# PostgreSQL; `DATABASE_URL` is the single switch between the two.
SQLITE_PREFIXES = ("sqlite:///", "sqlite://")


class Settings(BaseSettings):
    """Runtime configuration for the CipherQuest API."""

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    secret_key: str = Field(default="change_me_in_local_env_only")

    database_url: str = Field(default=f"sqlite:///{BACKEND_DIR / 'data' / 'cipherquest.db'}")

    frontend_origin: str = Field(default="http://localhost:5173")
    api_base_url: str = Field(default="http://localhost:8000")

    rate_limit_per_minute: int = Field(default=60)

    @field_validator("database_url")
    @classmethod
    def _strip_whitespace(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("DATABASE_URL must not be empty")
        return value

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith(SQLITE_PREFIXES)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
