# Changelog

Версії за semantic versioning (MAJOR.MINOR.PATCH). Кожна лабораторна робота — нова MINOR-версія,
перша production-версія — 1.0.0.

## [1.0.0] — 2026-09-29 (лабораторна робота №10)

- Конфігурація зі змінних середовища та `.env` (pydantic-settings): `APP_NAME`, `ENVIRONMENT`, `DATABASE_URL`,
  `LOG_LEVEL`, `HOST`, `PORT`; `.env.example` без секретів.
- `GET /health`; logging з рівнем `LOG_LEVEL`; `restaurant-orders` запускає production-сервіс (міграції + uvicorn).
- Пакет: metadata, LICENSE, wheel і sdist (`python -m build`).
- Docker: multi-stage build, non-root user, `HEALTHCHECK`, volume для SQLite.
- CI на GitHub Actions: ruff check, ruff format --check, mypy, pytest з coverage (Python 3.11 і 3.12),
  package build з артефактом, Docker build з перевіркою `/health`.
- Код відформатовано Ruff; демонстрацію ЛР9 перенесено в `restaurant_orders.optimization_demo`.

## [0.9.0] — лабораторна робота №9

Профілювання й оптимізація статистики історії замовлень: cProfile, tracemalloc, threads, processes, NumPy, caching.

## [0.8.0] — лабораторна робота №8

REST API на FastAPI, Pydantic-схеми, асинхронний клієнт HTTPX.

## [0.7.0] — лабораторна робота №7

База даних SQLite: SQLAlchemy ORM, repositories, транзакції, міграції Alembic.

## [0.1.0 – 0.6.0] — лабораторні роботи №1–6

Структура проєкту, аналіз даних, потокова обробка, ООП-модель, імпорт/експорт, автоматизовані тести.
