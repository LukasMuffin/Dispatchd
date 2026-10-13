"""Application settings, loaded from environment variables prefixed with DISPATCHD_."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DISPATCHD_")

    database_url: str = "postgresql://dispatchd:dispatchd@localhost:5432/dispatchd"
    log_level: str = "INFO"
    worker_poll_interval_seconds: float = 1.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
