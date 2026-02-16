from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Required (Pydantic will raise error if missing in Env, unless we handle it)
    # BUT since we want to handle it gracefully in main.py, use None default:
    GOOGLE_SEARCH_API_KEY: str | None = None
    GOOGLE_SEARCH_CX: str | None = None
    OPENAI_API_KEY: str | None = None

    # Optional
    OPENALEX_API_KEY: str | None = None
    GOOGLE_CREDENTIALS: str | None = None
    SHEET_ID: str | None = None
    SHEET_URL: str | None = None
    CHAT_MODEL: str = "gpt-4o-mini"

    PROJECT_NAME: str = "Nesta Signal Scout"
    # Set BACKEND_CORS_ORIGINS in .env as a JSON array, e.g.
    # BACKEND_CORS_ORIGINS=["https://nesta-signal-scout.onrender.com"]
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:8000",
            "https://nesta-signal-scout.onrender.com",
        ],
        validation_alias=AliasChoices("BACKEND_CORS_ORIGINS", "CORS_ORIGINS"),
    )


SCAN_RESULT_LIMIT: int = 6
DEFAULT_SEARCH_RESULTS: int = 10
SEARCH_TIMEOUT_SECONDS: int = 20


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
