"""Application configuration via environment variables / .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "sqlite:///./kn0.db"

    # File storage
    upload_dir: Path = Path("./uploads")

    # spaCy model to load
    spacy_model: str = "en_core_web_sm"

    # Entity resolution thresholds
    merge_threshold: float = 0.85   # above → auto-merge
    review_threshold: float = 0.65  # between → flag UNDER_REVIEW

    # Confidence scoring
    min_confidence_display: float = 0.3
    source_reliability_default: float = 0.5

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000


settings = Settings()
