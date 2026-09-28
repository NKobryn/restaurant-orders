"""Loading and validation of the YAML configuration."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from restaurant_orders.data_io.exceptions import ConfigurationError

SUPPORTED_SCHEMA_VERSION = 1
CONFIG_ENV_VARIABLE = "RESTAURANT_CONFIG"


@dataclass(frozen=True, slots=True)
class ValidationRules:
    """Rules that every order position must satisfy."""

    allowed_categories: frozenset[str]
    min_price: float
    max_price: float


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    """Where and how detailed the application writes its log."""

    level: str
    path: Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Complete configuration of the import/export application."""

    input_path: Path
    output_path: Path
    errors_path: Path
    summary_path: Path
    skip_invalid: bool
    rules: ValidationRules
    logging: LoggingConfig


def default_config_path() -> Path:
    """Return the path from RESTAURANT_CONFIG or config.yaml in the current folder."""
    return Path(os.environ.get(CONFIG_ENV_VARIABLE, "config.yaml"))


def read_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML file into a dictionary."""
    try:
        with path.open("r", encoding="utf-8") as file:
            raw = yaml.safe_load(file)
    except FileNotFoundError as error:
        raise ConfigurationError(f"Файл конфігурації не знайдено: {path}") from error
    except yaml.YAMLError as error:
        raise ConfigurationError(f"Некоректний YAML у файлі {path}") from error
    if not isinstance(raw, dict):
        raise ConfigurationError(f"Конфігурація {path} має бути словником YAML.")
    return raw


def load_config(path: Path) -> AppConfig:
    """Load, convert and validate the configuration; raise ConfigurationError on problems."""
    raw = read_yaml(path)
    try:
        if raw["schema_version"] != SUPPORTED_SCHEMA_VERSION:
            raise ConfigurationError(f"Непідтримувана версія схеми: {raw['schema_version']}.")
        processing = raw["processing"]
        config = AppConfig(
            input_path=Path(raw["input"]["path"]),
            output_path=Path(raw["output"]["path"]),
            errors_path=Path(raw["output"]["errors_path"]),
            summary_path=Path(raw["output"]["summary_path"]),
            skip_invalid=bool(processing["skip_invalid"]),
            rules=ValidationRules(
                allowed_categories=frozenset(str(name) for name in processing["allowed_categories"]),
                min_price=float(processing["price_range"]["min"]),
                max_price=float(processing["price_range"]["max"]),
            ),
            logging=LoggingConfig(level=str(raw["logging"]["level"]), path=Path(raw["logging"]["path"])),
        )
    except KeyError as error:
        raise ConfigurationError(f"У конфігурації бракує ключа {error}.") from error
    except (TypeError, ValueError) as error:
        raise ConfigurationError("Некоректна структура або значення конфігурації.") from error
    validate_config(config)
    return config


def validate_config(config: AppConfig) -> None:
    """Fail fast if the configuration values cannot work."""
    rules = config.rules
    if not rules.allowed_categories:
        raise ConfigurationError("Список allowed_categories порожній.")
    if not 0 < rules.min_price <= rules.max_price:
        raise ConfigurationError(f"Некоректний діапазон цін: {rules.min_price}–{rules.max_price}.")
    if config.logging.level.upper() not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ConfigurationError(f"Невідомий рівень логування: {config.logging.level}.")
    if not config.input_path.is_file():
        raise ConfigurationError(f"Вхідний файл не знайдено: {config.input_path}")
    for output in (config.output_path, config.errors_path, config.summary_path):
        if not output.parent.is_dir():
            raise ConfigurationError(f"Каталог для результату не існує: {output.parent}")
