# Restaurant Orders

Навчальний проєкт з курсу «Професійний Python», варіант №11 — «Облік замовлень ресторану».
Проєкт розвивається від лабораторної до лабораторної:

- лабораторна робота №1 — структура проєкту, моделі, business logic, консольне меню;
- лабораторна робота №2 — аналіз замовлень за допомогою структур даних Python;
- лабораторна робота №3 — потокова обробка великих CSV-файлів замовлень (iterators, generators, itertools);
- лабораторна робота №4 — типізована ООП-модель ресторану (dataclass, ABC, Protocol, Generic, SOLID, mypy);
- лабораторна робота №5 — надійний імпорт/експорт замовлень (exceptions, context managers, logging, CSV/JSON/YAML);
- лабораторна робота №6 — автоматизоване тестування (pytest, fixtures, mocks, AsyncMock, coverage) і повний сценарій замовлення.

## Можливості

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

## Вимоги

Python 3.11 або новішої версії.

## Встановлення

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows
python -m pip install -e ".[dev]"   # PyYAML, а також mypy, types-PyYAML, pytest, pytest-cov
```

## Запуск

Головна точка входу — поточна лабораторна робота (№6): повний сценарій замовлення — імпорт
`data/orders.csv` за `config.yaml` → замовлення → оплата (ліміт картки 450 грн) → асинхронна доставка.
Код завершення 0 — успіх, 1 — помилка конфігурації. Те саме запускає команда `restaurant-orders`:

```bash
python -m restaurant_orders.main                 # config.yaml за замовчуванням
RESTAURANT_CONFIG=інший.yaml python -m restaurant_orders.main
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

## Тести і перевірка типів

```bash
pytest                                # увесь test suite (unit + integration)
pytest -v -m integration              # лише інтеграційні тести
pytest --cov                          # statement + branch coverage, поріг 80 %
pytest --cov --cov-report=html        # HTML-звіт у htmlcov/index.html
mypy                                  # налаштування strict у pyproject.toml
```

Експерименти з тестування: `experiments/testing/README.md`.

## Структура проєкту

```text
restaurant_orders/
├── pyproject.toml
├── README.md
├── .gitignore
├── config.yaml                 # конфігурація імпорту (ЛР5)
├── data/
│   ├── orders_sample.csv       # малий приклад із помилками (ЛР3)
│   ├── orders.csv              # вхідні дані ЛР5 (з некоректними рядками)
│   └── orders.jsonl            # ті самі дані у форматі JSON Lines (ЛР5)
├── output/, logs/              # результати й журнал імпорту (не комітяться)
├── src/restaurant_orders/
│   ├── __init__.py
│   ├── main.py                 # головна точка входу: поточна лабораторна (ЛР6, сценарій замовлення)
│   ├── flow.py                 # імпорт → замовлення → оплата → доставка (ЛР6)
│   ├── console.py              # консольне меню (ЛР1)
│   ├── models.py               # Dish, Order (ЛР1), OrderItemRecord, OrderSummary (ЛР3)
│   ├── services.py             # business logic (ЛР1)
│   ├── data.py                 # демонстраційне меню і замовлення (ЛР2)
│   ├── processors.py           # list, set, dict, Counter (ЛР2)
│   ├── analytics.py            # статистика, closure, *args, **kwargs (ЛР2)
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
└── tests/
    ├── conftest.py                           # спільні fixtures (ЛР6)
    ├── unit/                                 # тести ЛР1–5 (unittest) і нові pytest-тести ЛР6
    └── integration/                          # import pipeline, order flow, консольні застосунки (ЛР6)
```
