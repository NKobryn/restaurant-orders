"""Application configuration from environment variables and an optional .env file (laboratory work 10)."""

import logging
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DATABASE_URL = "sqlite:///restaurant.db"


class Settings(BaseSettings):
    """Settings of the service; every field can be set by the environment variable with the same name."""

    app_name: str = "Restaurant Orders API"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = DEFAULT_DATABASE_URL
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Read the settings once and reuse them."""
    return Settings()


def configure_logging(settings: Settings) -> None:
    """Configure logging of the whole application with LOG_LEVEL."""
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger().setLevel(settings.log_level)
