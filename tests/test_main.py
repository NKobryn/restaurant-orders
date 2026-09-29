"""Tests of the production entry point (laboratory work 10)."""

import logging
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import inspect

from restaurant_orders import main as service
from restaurant_orders.persistence.database import create_database_engine

TABLES = {"categories", "dishes", "orders", "order_items"}


def tables(url: str) -> set[str]:
    engine = create_database_engine(url)
    names = set(inspect(engine).get_table_names())
    engine.dispose()
    return names


def test_database_is_created_by_migrations_in_the_project(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'service.db'}"
    assert service.prepare_database(url) == "alembic upgrade head"
    assert TABLES | {"alembic_version"} <= tables(url)


def test_database_is_created_without_alembic_ini(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    url = f"sqlite:///{tmp_path / 'wheel.db'}"
    assert service.prepare_database(url) == "create_all"
    assert TABLES <= tables(url)


def test_main_starts_uvicorn_with_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(service.uvicorn, "run", lambda app, **options: calls.append({"app": app, **options}))
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'main.db'}")
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    logging.disable(logging.NOTSET)  # the autouse fixture quiet_logging silences logging in every test
    service.main()
    assert calls == [
        {"app": "restaurant_orders.api.app:app", "host": "0.0.0.0", "port": 8080, "log_level": "info", "reload": False}
    ]
    log = caplog.text
    assert "Restaurant Orders" in log and "environment: production" in log
    assert "is ready (alembic upgrade head)" in log
