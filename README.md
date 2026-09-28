# Restaurant Orders

Навчальний проєкт з курсу «Професійний Python», варіант №11 — «Облік замовлень ресторану».
Проєкт розвивається від лабораторної до лабораторної:

- лабораторна робота №1 — структура проєкту, моделі, business logic, консольне меню;
- лабораторна робота №2 — аналіз замовлень за допомогою структур даних Python;
- лабораторна робота №3 — потокова обробка великих CSV-файлів замовлень (iterators, generators, itertools);
- лабораторна робота №4 — типізована ООП-модель ресторану (dataclass, ABC, Protocol, Generic, SOLID, mypy).

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

## Вимоги

Python 3.11 або новішої версії.

## Встановлення

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows
python -m pip install -e ".[dev]"   # разом із mypy
```

## Запуск

Головна точка входу показує поточну лабораторну роботу (№4 — ООП-модель ресторану);
після editable installation те саме запускає команда `restaurant-orders`:

```bash
python -m restaurant_orders.main
```

Експерименти лабораторної роботи №4 (dependency injection, inheritance vs composition):

```bash
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
python -m unittest discover -s tests -v
mypy                                  # налаштування strict у pyproject.toml
```

## Структура проєкту

```text
restaurant_orders/
├── pyproject.toml
├── README.md
├── .gitignore
├── src/restaurant_orders/
│   ├── __init__.py
│   ├── main.py        # головна точка входу: демо поточної лабораторної (ЛР4)
│   ├── console.py     # консольне меню (ЛР1)
│   ├── models.py      # dataclass Dish і Order
│   ├── services.py    # business logic (ЛР1)
│   ├── data.py        # демонстраційне меню і замовлення (ЛР2)
│   ├── processors.py  # перетворення замовлень у list, set, dict, Counter (ЛР2)
│   ├── analytics.py   # статистика, closure, *args, **kwargs (ЛР2)
│   ├── decorators.py  # measure_time, track_operation, історія deque (ЛР2)
│   ├── analysis.py    # точка входу аналізу (ЛР2)
│   ├── benchmark.py   # порівняння пошуку list / dict / set (ЛР2)
│   ├── stream/        # потокова обробка (ЛР3)
│       ├── iterators.py    # OrderIdSequence, endless_order_ids
│       ├── readers.py      # read_lines, read_many (chain)
│       ├── parsers.py      # clean_lines, parse_rows
│       ├── validation.py   # validate_records, лічильник помилок
│       ├── filters.py      # filter_by_category, first_orders, find_first
│       ├── pipeline.py     # groupby, batched, build_pipeline
│       ├── analytics.py    # статистика, accumulate, batch_reports
│       ├── export.py       # потоковий експорт у CSV
│       ├── dataset.py      # генератор великих CSV
│       ├── main.py         # точка входу ЛР3
│       └── experiment.py   # eager проти lazy
│   └── domain/        # типізована ООП-модель (ЛР4)
│       ├── value_objects.py  # Money
│       ├── models.py         # Dish, OrderItem, Order, OrderStatus, Menu
│       ├── protocols.py      # HasId, PaymentGateway, KitchenNotifier
│       ├── repositories.py   # Repository[T], InMemoryRepository[T]
│       ├── pricing.py        # PricingPolicy, NoDiscount, CategoryDiscount
│       ├── dto.py            # DishPayload (TypedDict)
│       ├── adapters.py       # DemoPaymentGateway, LimitedPaymentGateway, ConsoleKitchenNotifier
│       ├── exceptions.py     # RestaurantError і нащадки
│       ├── services.py       # RestaurantService
│       └── experiments.py    # DI, inheritance vs composition
├── data/orders_sample.csv  # малий приклад із помилками (ЛР3)
└── tests/
    ├── test_services.py
    ├── test_analytics.py
    ├── test_stream.py
    └── test_domain.py
```
