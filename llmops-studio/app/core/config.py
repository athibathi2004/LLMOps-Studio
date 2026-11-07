"""Application configuration and settings."""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings with environment variable support."""

    APP_NAME: str = "LLMOps Studio"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "llmops-studio-default-dev-secret-key-change-in-prod"

    # Server binding
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./llmops_studio.db"

    # LLM Providers defaults
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_TIMEOUT_SECONDS: int = 30
    MAX_OUTPUT_TOKENS: int = 2048
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_TOP_P: float = 1.0

    # Logging & Observability
    LOG_LEVEL: str = "INFO"
    STRUCTURED_LOGS: bool = True
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

