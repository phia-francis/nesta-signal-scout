from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    OPENAI_API_KEY: str | None = None
    GOOGLE_SEARCH_API_KEY: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "Google Search_API_KEY",
            "Google_Search_API_KEY",
            "GOOGLE_SEARCH_API_KEY",
            "GOOGLE_SEARCH_KEY",
        ),
    )
    GOOGLE_SEARCH_CX: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "Google Search_CX",
            "Google_Search_CX",
            "GOOGLE_SEARCH_CX",
        ),
    )
    GOOGLE_CREDENTIALS: str | None = None
    SHEET_ID: str | None = None
    CHAT_MODEL: str = "gpt-4o-mini"
    GTR_API_KEY: str | None = None
    OPENALEX_API_KEY: str | None = None

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
