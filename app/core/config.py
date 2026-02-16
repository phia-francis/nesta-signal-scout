"""
Production-ready configuration with fail-fast validation.
Environment variables MUST be present or app will not start.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Constants
SCAN_RESULT_LIMIT = 10
SEARCH_TIMEOUT_SECONDS = 15.0
DEFAULT_SEARCH_RESULTS = 10


class Settings(BaseSettings):
    """
    Application settings with strict validation.
    All API keys are REQUIRED - app will fail fast if missing.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # REQUIRED: OpenAI Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_MAX_TOKENS: int = 2000

    # REQUIRED: Google Search Configuration
    GOOGLE_SEARCH_API_KEY: str
    GOOGLE_SEARCH_CX: str

    # REQUIRED: Google Sheets Configuration
    GOOGLE_CREDENTIALS: str  # JSON string of service account credentials
    SHEET_ID: str
    SHEET_URL: str | None = None

    # OPTIONAL: OpenAlex Configuration (graceful degradation if missing)
    OPENALEX_API_KEY: str | None = None

    # OPTIONAL: Application Settings
    CRON_SECRET: str | None = None
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "production"
    PYTHON_VERSION: str | None = None

    @field_validator("OPENAI_API_KEY", "GOOGLE_SEARCH_API_KEY", "GOOGLE_SEARCH_CX", "GOOGLE_CREDENTIALS", "SHEET_ID")
    @classmethod
    def validate_required_not_empty(cls, v: str, info) -> str:
        """Ensure required fields are not empty strings."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def validate_google_credentials_json(self) -> "Settings":
        """Validate that GOOGLE_CREDENTIALS is valid JSON."""
        try:
            credentials_dict = json.loads(self.GOOGLE_CREDENTIALS)
            if not isinstance(credentials_dict, dict):
                raise ValueError("GOOGLE_CREDENTIALS must be a JSON object")
            # Verify essential Google service account fields
            required_fields = ["type", "project_id", "private_key", "client_email"]
            missing_fields = [field for field in required_fields if field not in credentials_dict]
            if missing_fields:
                raise ValueError(f"GOOGLE_CREDENTIALS missing required fields: {', '.join(missing_fields)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"GOOGLE_CREDENTIALS is not valid JSON: {e}") from e
        return self

    def log_startup_summary(self) -> None:
        """Log configuration summary on startup (without leaking secrets)."""
        logger.info("=" * 60)
        logger.info("Nesta Signal Scout - Configuration")
        logger.info("=" * 60)
        logger.info("Environment: %s", self.ENVIRONMENT)
        logger.info("Log Level: %s", self.LOG_LEVEL)
        logger.info("OpenAI Model: %s", self.OPENAI_MODEL)
        logger.info("OpenAI API Key: %s", "✓ Present" if self.OPENAI_API_KEY else "✗ Missing")
        logger.info("Google Search API Key: %s", "✓ Present" if self.GOOGLE_SEARCH_API_KEY else "✗ Missing")
        logger.info("Google Search CX: %s", "✓ Present" if self.GOOGLE_SEARCH_CX else "✗ Missing")
        logger.info("Google Credentials: %s", "✓ Present" if self.GOOGLE_CREDENTIALS else "✗ Missing")
        logger.info("Google Sheet ID: %s", self.SHEET_ID[:8] + "..." if len(self.SHEET_ID) > 8 else self.SHEET_ID)
        logger.info("OpenAlex API Key: %s", "✓ Present" if self.OPENALEX_API_KEY else "○ Optional (not set)")
        logger.info("Cron Secret: %s", "✓ Configured" if self.CRON_SECRET else "○ Not configured")
        logger.info("=" * 60)


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Will raise ValidationError at import time if configuration is invalid.
    """
    settings = Settings()
    settings.log_startup_summary()
    return settings
