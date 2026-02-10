from __future__ import annotations

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
    CRUNCHBASE_API_KEY: str | None = None

    PROJECT_NAME: str = "Nesta Signal Scout"
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])


SCAN_RESULT_LIMIT: int = 6
DEFAULT_SEARCH_RESULTS: int = 10
SEARCH_TIMEOUT_SECONDS: int = 20
