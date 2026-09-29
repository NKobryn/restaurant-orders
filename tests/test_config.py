"""Tests of the configuration from environment variables (laboratory work 10)."""

import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from restaurant_orders.config import Settings, configure_logging, get_settings

VARIABLES = ["APP_NAME", "ENVIRONMENT", "DATABASE_URL", "LOG_LEVEL", "HOST", "PORT"]


@pytest.fixture
def clean_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No settings in the environment and no .env file in the working directory."""
    for name in VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)


def test_default_settings(clean_environment: None) -> None:
    settings = Settings()
    assert settings.environment == "development"
    assert settings.database_url == "sqlite:///restaurant.db"
    assert (settings.log_level, settings.host, settings.port) == ("INFO", "127.0.0.1", 8000)


def test_environment_variables_override_defaults(clean_environment: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////app/data/restaurant.db")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PORT", "9000")
    settings = get_settings()
    assert settings.environment == "production"
    assert settings.database_url == "sqlite:////app/data/restaurant.db"
    assert (settings.log_level, settings.port) == ("DEBUG", 9000)
    assert get_settings() is settings


def test_settings_from_env_file(clean_environment: None, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("ENVIRONMENT=test\nLOG_LEVEL=WARNING\n", encoding="utf-8")
    settings = Settings()
    assert (settings.environment, settings.log_level) == ("test", "WARNING")


@pytest.mark.parametrize(("name", "value"), [("ENVIRONMENT", "staging"), ("LOG_LEVEL", "LOUD"), ("PORT", "abc")])
def test_invalid_settings_are_rejected(
    clean_environment: None, monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError, match=name.lower()):
        Settings()


def test_configure_logging_uses_log_level(clean_environment: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    configure_logging(Settings())
    assert logging.getLogger().level == logging.WARNING
    configure_logging(Settings(log_level="INFO"))
    assert logging.getLogger().level == logging.INFO
