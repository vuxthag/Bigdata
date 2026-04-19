"""
config.py
=========
Application settings loaded from environment variables / .env file.
Uses pydantic-settings for type-safe config.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost/jobrec"

    # ── Auth ──────────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-this-to-a-random-secret-key-min-32-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # ── Google OAuth ────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""

    # ── Sentence-BERT ─────────────────────────────────────────────────────────
    SBERT_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # ── Continual Learning ────────────────────────────────────────────────────
    RETRAIN_THRESHOLD: int = 100          # interactions before retraining
    MODEL_CHECKPOINT_DIR: str = "ml_checkpoints/"
    RETRAIN_SCHEDULE_HOURS: int = 1       # APScheduler interval

    # ── File Upload ───────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10

    # ── Data ──────────────────────────────────────────────────────────────────
    SEED_DATA_PATH: str = "data/jobs_full_all.csv"

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


# Singleton instance used everywhere in the app
settings = Settings()
