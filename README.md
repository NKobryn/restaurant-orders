# Restaurant Orders

Облік замовлень ресторану — навчальний проєкт з курсу «Професійний Python», варіант №11.
Сервіс веде меню (страви з назвою, категорією й ціною) і замовлення (номер і список страв): створює
замовлення, додає й видаляє страви, рахує суму замовлення, знаходить найдорожчу страву й середній чек.
Дані зберігаються в SQLite через SQLAlchemy та міграції Alembic, доступ — через REST API на FastAPI.
Проєкт пакується як `restaurant-orders` (модуль `restaurant_orders`), запускається в Docker і
перевіряється в GitHub Actions.

![CI](https://github.com/NKobryn/restaurant-orders/actions/workflows/ci.yml/badge.svg)

## Можливості

- REST API: меню, категорії, замовлення, позиції, суми, статистика, `GET /health`;
- база даних SQLite: ORM-моделі, repositories, транзакції, міграції Alembic (ЛР7);
- валідація запитів Pydantic і структуровані помилки 404 / 409 / 422 (ЛР8);
- аналітика великої історії замовлень із NumPy і кешем статистики (ЛР9);
- конфігурація через змінні середовища або `.env`, logging з рівнем `LOG_LEVEL`;
- Python package (wheel, sdist), Docker image з volume для бази, CI/CD на GitHub Actions.

Архітектура:

```text
Client (curl, Swagger UI, httpx)
   │
   ▼
FastAPI  api/app.py  (Pydantic-схеми, обробники помилок, /health)
   │
   ▼
Service  persistence/services.py  (OrderService: транзакції, суми, статистика)
   │
   ▼
Repository  persistence/repositories.py  (Category/Dish/OrderRepository)
   │
   ▼
Database  SQLite (DATABASE_URL), схема — міграції Alembic
```

## Вимоги

Python 3.11 або 3.12; для контейнера — Docker.

## Встановлення

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows
python -m pip install -e ".[dev]"   # застосунок + засоби розробки (pytest, mypy, ruff, build)
```

Встановлення готового пакета (wheel) без вихідного коду:

```bash
python -m build                                     # dist/restaurant_orders-<версія>-py3-none-any.whl і .tar.gz
python -m venv /tmp/clean-env
/tmp/clean-env/bin/pip install dist/restaurant_orders-*.whl
/tmp/clean-env/bin/restaurant-orders                # сервіс на http://127.0.0.1:8000
```

## Конфігурація

Налаштування читаються зі змінних середовища, а якщо їх немає — з файлу `.env` у поточній папці
(`src/restaurant_orders/config.py`, pydantic-settings). Приклад без секретів — `.env.example`:

```bash
cp .env.example .env            # .env не потрапляє в Git (.gitignore)
```

| Змінна | За замовчуванням | Призначення |
|---|---|---|
| `APP_NAME` | `Restaurant Orders API` | назва сервісу в OpenAPI |
| `ENVIRONMENT` | `development` | `development`, `test` або `production` (у development — auto-reload) |
| `DATABASE_URL` | `sqlite:///restaurant.db` | адреса бази даних SQLAlchemy |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `HOST`, `PORT` | `127.0.0.1`, `8000` | адреса й порт сервера |

Секретів (паролів, токенів, ключів) проєкт не має; якщо з'являться — лише через змінні середовища,
`.env` або GitHub Secrets, ніколи в коді, README, Dockerfile чи Git.

## Запуск локально

```bash
restaurant-orders               # або python -m restaurant_orders.main
LOG_LEVEL=DEBUG ENVIRONMENT=production restaurant-orders   # інша конфігурація без зміни коду
```

`restaurant-orders` налаштовує logging, застосовує міграції (`alembic upgrade head`; без `alembic.ini` поруч —
створює таблиці) і запускає uvicorn. Документація API: http://127.0.0.1:8000/docs (Swagger UI),
http://127.0.0.1:8000/redoc, схема — http://127.0.0.1:8000/openapi.json.

## Docker

```bash
docker build -t restaurant-orders:1.0.0 .
docker run -d --name restaurant-orders -p 8000:8000 \
    -v restaurant_data:/app/data \
    -e ENVIRONMENT=production -e LOG_LEVEL=INFO \
    restaurant-orders:1.0.0
curl http://127.0.0.1:8000/health         # {"status":"ok","environment":"production"}
docker logs restaurant-orders
docker stop restaurant-orders && docker rm restaurant-orders
```

Dockerfile — multi-stage build (стадія `builder` збирає wheel, фінальний образ встановлює лише wheel),
користувач без прав root `appuser`, `HEALTHCHECK` на `/health`, міграції при старті контейнера.
База SQLite — `DATABASE_URL=sqlite:////app/data/restaurant.db` у volume `/app/data`, тому дані
зберігаються після перезапуску контейнера.

## REST API

| Метод | Шлях | Що робить |
|---|---|---|
| GET | `/health` | стан сервісу й environment (200) |
| GET | `/dishes?category=&sort=&limit=&offset=` | меню з фільтром, сортуванням, пагінацією |
| GET / POST | `/dishes/{id}`, `/dishes` | страва; нова страва (201) |
| PATCH / DELETE | `/dishes/{id}` | зміна ціни чи категорії; видалення (204, 409 якщо є в замовленнях) |
| GET | `/categories` | категорії з кількістю страв |
| GET / POST | `/orders?limit=&offset=`, `/orders` | історія; нове замовлення однією транзакцією (201) |
| GET | `/orders/{id}`, `/orders/{id}/total` | замовлення з найдорожчою позицією; сума |
| POST / DELETE | `/orders/{id}/items`, `/orders/{id}/items/{item_id}` | додати (201) / видалити (204) позицію |
| GET | `/orders/statistics` | кількість, середня вартість, виручка за категоріями |

Приклад:

```bash
curl -X POST http://127.0.0.1:8000/dishes -H "Content-Type: application/json" \
     -d '{"name": "Борщ", "category": "Перші страви", "price": 95}'
curl -X POST http://127.0.0.1:8000/orders -H "Content-Type: application/json" \
     -d '{"id": 1, "items": [{"dish": "Борщ", "quantity": 2}]}'
curl http://127.0.0.1:8000/orders/1/total    # {"order_id":1,"items_count":1,"total":190.0}
```

## Тести і якість коду

```bash
ruff check .                          # lint (pycodestyle, pyflakes, isort)
ruff format --check .                 # форматування
mypy                                  # strict type checking (src і benchmarks)
pytest -v                             # увесь test suite (unit + integration)
pytest --cov                          # statement + branch coverage, поріг 80 %
```

## CI/CD

`.github/workflows/ci.yml` запускається на кожен push у `main`, на теги `v*` і pull requests:

1. **quality** (Python 3.11 і 3.12): `ruff check .`, `ruff format --check .`, `mypy`, `pytest -v --cov` (поріг 80 %);
2. **build**: `python -m build`, перелік `dist/`, встановлення wheel у чистий venv, артефакт `dist`;
3. **docker**: `docker build`, запуск контейнера і перевірка `GET /health`.

Зелений pipeline означає, що всі три jobs пройшли.

## Сценарій демонстрації

1. `pytest -v`, `ruff check .`, `mypy` — тести й якість коду.
2. `python -m build` — wheel і sdist у `dist/`.
3. `docker build -t restaurant-orders:1.0.0 .` і `docker run …` (розділ Docker).
4. http://127.0.0.1:8000/health і http://127.0.0.1:8000/docs — створити страви Борщ і Узвар,
   замовлення №1 (Борщ × 2, Узвар), подивитися `GET /orders/1` (найдорожча страва) і `GET /orders/1/total`.
5. `docker rm -f restaurant-orders`, знову `docker run …` з тим самим volume — меню й замовлення збереглися.
6. GitHub → Actions: зелений pipeline.

## Розвиток проєкту (ЛР1–10)

- лабораторна робота №1 — структура проєкту, моделі, business logic, консольне меню;
- лабораторна робота №2 — аналіз замовлень за допомогою структур даних Python;
- лабораторна робота №3 — потокова обробка великих CSV-файлів замовлень (iterators, generators, itertools);
- лабораторна робота №4 — типізована ООП-модель ресторану (dataclass, ABC, Protocol, Generic, SOLID, mypy);
- лабораторна робота №5 — надійний імпорт/експорт замовлень (exceptions, context managers, logging, CSV/JSON/YAML);
- лабораторна робота №6 — автоматизоване тестування (pytest, fixtures, mocks, AsyncMock, coverage);
- лабораторна робота №7 — база даних SQLite: SQLAlchemy ORM, repositories, транзакції, DB-API, міграції Alembic;
- лабораторна робота №8 — REST API на FastAPI, Pydantic, асинхронний клієнт HTTPX;
- лабораторна робота №9 — профілювання й оптимізація (cProfile, tracemalloc, threads, processes, NumPy, caching);
- лабораторна робота №10 — production: configuration, packaging, Docker, CI/CD.

Можливості ЛР1 (консольний застосунок):

- створення замовлень і додавання страв;
- підрахунок суми кожного замовлення;
- пошук найдорожчої позиції в замовленні;
- обчислення середньої вартості замовлень;
- сортування замовлень за сумою;
- інтерактивне меню з перевіркою введених даних.

Лабораторна робота №2 («Аналіз замовлень ресторану»):

- унікальні страви та категорії (set);
- сума кожного замовлення і середня вартість замовлення;
- найдорожча позиція і найпопулярніша страва (Counter);
- групування позицій за замовленнями (defaultdict), рейтинг замовлень;
- пошук замовлення за номером через dict-index;
- фільтри через closure і lambda, decorators, історія операцій (deque);
- benchmark пошуку в list, dict і set на 1 000, 10 000 і 100 000 записів.

Лабораторна робота №3 («Потокова обробка замовлень ресторану», CSV `order_id,dish,category,price,quantity`):

- власний iterator `OrderIdSequence`, нескінченний generator номерів + `islice`;
- lazy pipeline: читання (`yield from`) → очищення → parsing → validation → `groupby` за замовленням;
- підрахунок некоректних рядків, lazy filter за категорією, перші N замовлень за умовою;
- потоковий середній чек (`accumulate`), batch processing, потоковий експорт сум у CSV;
- експеримент eager проти lazy: час, пікова пам'ять (tracemalloc), time to first result, early termination.

Лабораторна робота №4 («Система обліку замовлень ресторану», пакет `restaurant_orders.domain`):

- value object `Money` (frozen dataclass, `+`, `*`, порівняння через `total_ordering`);
- сутності `Dish` (ціна через property), `OrderItem`, `Order` (композиція позицій, статус), колекція `Menu`;
- `Repository[T]` (ABC + Generic, `TypeVar` з bound) і `InMemoryRepository[T]`;
- `PaymentGateway`, `KitchenNotifier` (Protocol), стратегії ціни `PricingPolicy` (ABC);
- `DishPayload` (TypedDict), ієрархія винятків `RestaurantError`;
- `RestaurantService` — створення замовлення, страви, сума, найдорожча страва, середня вартість,
  оплата й сповіщення кухні; усі залежності передаються в конструктор (dependency injection);
- перевірка типів `mypy --strict`, експерименти DI і inheritance vs composition.

Лабораторна робота №5 («Імпорт та експорт замовлень ресторану», пакет `restaurant_orders.data_io`):

- конфігурація `config.yaml` (категорії, діапазон цін, strict/tolerant, шляхи, logging, schema_version);
- власна ієрархія винятків `ApplicationError` і exception chaining (`raise ... from error`);
- потокове читання CSV і JSON Lines через `Importer` Protocol, формат за розширенням файлу;
- валідація order_id, назви страви, дозволеної категорії, ціни в діапазоні, кількості > 0;
- strict (зупинка на першій помилці) і tolerant (пропуск із записом у log і в `invalid_orders.csv`);
- атомарний потоковий JSON-експорт, підсумок `summary.json`, власні context managers `atomic_write`, `logged_operation`;
- експерименти: strict vs tolerant, streaming vs eager, chaining, atomic output, помилки конфігурації.

Лабораторна робота №6 («Автоматизоване тестування», test suite у `tests/`):

- `tests/unit/` і `tests/integration/` (маркер `integration`), спільні fixtures у `tests/conftest.py`
  (fixture factories, parameterized і autouse fixtures, fake repository, autospec mocks);
- Mock / `return_value` / `side_effect` / interaction assertions, `AsyncMock` для асинхронної доставки,
  `tmp_path`, `monkeypatch` (змінні середовища, функції, `input`);
- statement і branch coverage з порогом 80 % у `pyproject.toml`, HTML-звіт;
- асинхронна служба доставки `domain/delivery.py` і повний сценарій замовлення `flow.py`;
- експерименти з тестування в `experiments/testing/` (не входять до основного набору).

Лабораторна робота №7 («Облік замовлень ресторану» з базою даних, пакет `restaurant_orders.persistence`):

- таблиці `categories`, `dishes`, `orders`, `order_items` (PK, FK з ON DELETE, UNIQUE, CHECK), SQLAlchemy 2.0 ORM;
- `CategoryRepository`, `DishRepository` (CRUD, фільтр, сортування, пагінація), `OrderRepository` (історія, видалення позицій);
- `OrderService`: оформлення замовлення однією транзакцією (commit / rollback), SUM, AVG, JOIN + GROUP BY;
- параметризований пошук страв за категорією через DB-API (`sqlite3`);
- міграції Alembic: `0001` — створення таблиць, `0002` — `orders.created_at` (upgrade і downgrade);
- `DATABASE_URL` задає базу (за замовчуванням `sqlite:///restaurant.db`).

Лабораторна робота №8 (REST API, пакет `restaurant_orders.api`):

| Метод | Шлях | Що робить |
|---|---|---|
| GET | `/dishes?category=&sort=&limit=&offset=` | меню з фільтром, сортуванням, пагінацією |
| GET / POST | `/dishes/{id}`, `/dishes` | страва; нова страва (201) |
| PATCH / DELETE | `/dishes/{id}` | зміна ціни чи категорії; видалення (204, 409 якщо є в замовленнях) |
| GET | `/categories` | категорії з кількістю страв |
| GET / POST | `/orders?limit=&offset=`, `/orders` | історія; нове замовлення однією транзакцією (201) |
| GET | `/orders/{id}`, `/orders/{id}/total` | замовлення з найдорожчою позицією; сума |
| POST / DELETE | `/orders/{id}/items`, `/orders/{id}/items/{item_id}` | додати (201) / видалити (204) позицію |
| GET | `/orders/statistics` | кількість, середня вартість, виручка за категоріями |

- Pydantic-схеми з валідацією (422), структуровані помилки `{"status", "error", "detail"}` (404, 409, 422);
- `api/client.py`: паралельне отримання сум замовлень — `asyncio.create_task` + `gather`, `Semaphore`,
  timeout (`asyncio.wait_for`), retry з експоненційною затримкою (`RetryPolicy`).

Лабораторна робота №9 (паралельність, багатопроцесність та оптимізація):

- `analytics.py`: генератор історії замовлень (10 000 / 100 000 / 1 000 000 замовлень), baseline `statistics_python`
  (суми замовлень, середній чек, найдорожче замовлення, найпопулярніша страва, оборот, категорії) і
  векторизована `statistics_numpy` (`np.bincount`); кеш `OrderHistory` + `lru_cache` з invalidation за версією даних;
- `parallel.py`: `ThreadPoolExecutor` і `ProcessPoolExecutor` за частинами історії, `multiprocessing.Process` + `Queue`,
  паралельне читання файлів замовлень, `threading.Thread` + `Lock` (race condition і її виправлення);
- `profiling.py`: повторні вимірювання (`perf_counter`, `timeit`), speedup, CSV результатів, текстові графіки,
  `cProfile` + `pstats`, `tracemalloc`;
- `benchmarks/`: експерименти й таблиці результатів (`benchmarks/results/benchmark_results.csv`).

### Запуск демонстрацій ЛР1–9

Експерименти лабораторної роботи №9 і профіль:

```bash
python benchmarks/benchmark_statistics.py   # усі реалізації для 3 розмірів даних + cold/warm cache
python benchmarks/benchmark_threads.py      # потоки: CPU-bound (GIL), читання файлів, race condition
python benchmarks/benchmark_processes.py    # процеси: 1, 2, 4, 8 workers, серіалізація, файли
python benchmarks/benchmark_numpy.py        # NumPy: час і пам'ять list проти масивів
python -m restaurant_orders.profiling       # cProfile і tracemalloc до та після оптимізації
```

Демонстрація оптимізації лабораторної роботи №9:

```bash
python -m restaurant_orders.optimization_demo
```

Демонстрація REST API лабораторної роботи №8 (база `restaurant.db` створюється заново):

```bash
python -m restaurant_orders.api.demo
```

Справжній HTTP-сервер і Swagger UI (http://127.0.0.1:8000/docs):

```bash
alembic upgrade head
uvicorn restaurant_orders.api.app:app --reload
```

Демонстрація бази даних лабораторної роботи №7:

```bash
python -m restaurant_orders.persistence.demo
```

Міграції вручну (Alembic):

```bash
alembic upgrade head        # створити / оновити схему
alembic current             # поточна ревізія
alembic downgrade 0001      # відкотити додавання created_at
```

Повний сценарій замовлення лабораторної роботи №6 (імпорт → оплата → асинхронна доставка):

```bash
python -m restaurant_orders.flow_app             # або RESTAURANT_CONFIG=інший.yaml
```

Застосунок імпорту/експорту лабораторної роботи №5 (результат у `output/`, журнал у `logs/import.log`):

```bash
python -m restaurant_orders.data_io.app          # або python -m restaurant_orders.data_io.app інший.yaml
```

Щоб змінити поведінку без редагування коду, змініть `config.yaml`: `skip_invalid: false` — strict mode,
`input.path: data/orders.jsonl` — імпорт JSON Lines, `price_range` чи `allowed_categories` — правила перевірки.

Експерименти лабораторної роботи №5 (близько 20 секунд):

```bash
python -m restaurant_orders.data_io.experiments
```

Лабораторна робота №4 — демонстрація ООП-моделі та експерименти DI і inheritance vs composition:

```bash
python -m restaurant_orders.domain.demo
python -m restaurant_orders.domain.experiments
```

Консольний застосунок лабораторної роботи №1 (демо та інтерактивне меню):

```bash
python -m restaurant_orders.console
python -m restaurant_orders.console --interactive
```

Аналіз замовлень (лабораторна робота №2):

```bash
python -m restaurant_orders.analysis
```

Benchmark пошуку в list, dict і set (виконується кілька секунд):

```bash
python -m restaurant_orders.benchmark
```

Потокова обробка замовлень (лабораторна робота №3; запускати з кореня проєкту, бо шляхи до
`data/` відносні; великий файл `data/generated/orders_100000.csv` створюється під час першого запуску):

```bash
python -m restaurant_orders.stream.main
```

Експеримент eager проти lazy на 10 000 / 100 000 / 500 000 і 1 000 000 записів (близько хвилини):

```bash
python -m restaurant_orders.stream.experiment
```

## Структура проєкту

```text
restaurant_orders/
├── pyproject.toml              # metadata, залежності, ruff, mypy, pytest, coverage
├── README.md, LICENSE, CHANGELOG.md
├── .gitignore, .env.example    # налаштування без секретів (ЛР10)
├── Dockerfile, .dockerignore   # образ сервісу (ЛР10)
├── .github/workflows/ci.yml    # CI/CD (ЛР10)
├── config.yaml                 # конфігурація імпорту (ЛР5)
├── alembic.ini, migrations/    # міграції бази даних (ЛР7)
├── data/
│   ├── orders_sample.csv       # малий приклад із помилками (ЛР3)
│   ├── orders.csv              # вхідні дані ЛР5 (з некоректними рядками)
│   └── orders.jsonl            # ті самі дані у форматі JSON Lines (ЛР5)
├── output/, logs/              # результати й журнал імпорту (не комітяться)
├── src/restaurant_orders/
│   ├── __init__.py
│   ├── main.py                 # головна точка входу: production-сервіс (ЛР10)
│   ├── config.py               # Settings, get_settings, configure_logging (ЛР10)
│   ├── optimization_demo.py    # демонстрація ЛР9
│   ├── flow.py, flow_app.py    # сценарій замовлення ЛР6 (логіка і застосунок)
│   ├── console.py              # консольне меню (ЛР1)
│   ├── models.py               # Dish, Order (ЛР1), OrderItemRecord, OrderSummary (ЛР3)
│   ├── services.py             # business logic (ЛР1)
│   ├── data.py                 # демонстраційне меню і замовлення (ЛР2)
│   ├── processors.py           # list, set, dict, Counter (ЛР2)
│   ├── analytics.py            # статистика, closure, *args, **kwargs (ЛР2); історія, NumPy, кеш (ЛР9)
│   ├── parallel.py             # потоки, процеси, Lock, читання файлів (ЛР9)
│   ├── profiling.py            # benchmark, speedup, CSV, cProfile, tracemalloc (ЛР9)
│   ├── decorators.py           # measure_time, track_operation (ЛР2)
│   ├── analysis.py             # точка входу аналізу (ЛР2)
│   ├── benchmark.py            # пошук у list / dict / set (ЛР2)
│   ├── stream/                 # потокова обробка (ЛР3)
│   │   ├── iterators.py, readers.py, parsers.py, validation.py
│   │   ├── filters.py, pipeline.py, analytics.py, export.py, dataset.py
│   │   ├── main.py             # точка входу ЛР3
│   │   └── experiment.py       # eager проти lazy
│   ├── domain/                 # типізована ООП-модель (ЛР4)
│   │   ├── value_objects.py    # Money
│   │   ├── models.py           # Dish, OrderItem, Order, OrderStatus, Menu
│   │   ├── protocols.py        # HasId, PaymentGateway, KitchenNotifier
│   │   ├── repositories.py     # Repository[T], InMemoryRepository[T]
│   │   ├── pricing.py          # PricingPolicy, NoDiscount, CategoryDiscount
│   │   ├── dto.py, adapters.py, exceptions.py, services.py
│   │   ├── delivery.py         # асинхронна доставка (ЛР6)
│   │   ├── demo.py             # демонстрація ЛР4
│   │   └── experiments.py      # DI, inheritance vs composition
│   ├── api/                    # REST API (ЛР8)
│   │   ├── app.py              # FastAPI: endpoints, обробники помилок
│   │   ├── schemas.py          # Pydantic-схеми
│   │   ├── dependencies.py     # сесія БД через Depends
│   │   ├── client.py           # httpx.AsyncClient: gather, Semaphore, timeout, retry
│   │   ├── transports.py       # транспорти для демонстрації затримки й збоїв
│   │   └── demo.py             # демонстрація REST API (ЛР8)
│   ├── persistence/            # база даних (ЛР7), demo.py — демо ЛР7
│   │   ├── database.py         # engine, sessions, DATABASE_URL, PRAGMA foreign_keys
│   │   ├── models.py           # ORM: Category, Dish, Order, OrderItem
│   │   ├── repositories.py     # Category/Dish/OrderRepository
│   │   ├── services.py         # OrderService: транзакції, SUM, AVG, GROUP BY
│   │   ├── dbapi.py            # sqlite3 + параметризований запит
│   │   └── migrations.py       # запуск Alembic із Python
│   └── data_io/                # надійний імпорт/експорт (ЛР5)
│       ├── exceptions.py       # ApplicationError і нащадки
│       ├── config.py           # AppConfig, load_config (YAML)
│       ├── logging_config.py   # configure_logging
│       ├── readers.py          # Importer, CsvImporter, JsonLinesImporter
│       ├── validators.py       # validate_row
│       ├── files.py            # atomic_write, logged_operation
│       ├── exporters.py        # export_json, errors_csv, export_summary
│       ├── services.py         # run_import, ImportStatistics
│       ├── app.py              # застосунок імпорту ЛР5
│       └── experiments.py      # експерименти ЛР5
├── experiments/testing/        # експерименти з тестування (ЛР6)
├── benchmarks/                 # експерименти ЛР9
│   ├── benchmark_statistics.py, benchmark_threads.py
│   ├── benchmark_processes.py, benchmark_numpy.py
│   └── results/benchmark_results.csv
└── tests/
    ├── conftest.py                           # спільні fixtures (ЛР6)
    ├── unit/                                 # тести ЛР1–5 (unittest) і нові pytest-тести ЛР6
    ├── integration/                          # ЛР6, база даних (ЛР7), API і async-клієнт (ЛР8)
    ├── test_parallel.py                      # правильність оптимізацій, Lock, кеш, вимірювання (ЛР9)
    ├── test_config.py                        # налаштування зі змінних середовища (ЛР10)
    └── test_main.py                          # production-запуск: міграції, uvicorn (ЛР10)
```
