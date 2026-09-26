# Restaurant Orders

Навчальний проєкт з курсу «Професійний Python», варіант №11 — «Облік замовлень ресторану».
Проєкт розвивається від лабораторної до лабораторної:

- лабораторна робота №1 — структура проєкту, моделі, business logic, консольне меню;
- лабораторна робота №2 — аналіз замовлень за допомогою структур даних Python.

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

## Вимоги

Python 3.11 або новішої версії.

## Встановлення

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows
python -m pip install -e .
```

## Запуск

Демонстраційний режим:

```bash
python -m restaurant_orders.main
```

Інтерактивний режим із введенням даних:

```bash
python -m restaurant_orders.main --interactive
```

Після editable installation також доступна команда `restaurant-orders`.

Аналіз замовлень (лабораторна робота №2):

```bash
python -m restaurant_orders.analysis
```

Benchmark пошуку в list, dict і set (виконується кілька секунд):

```bash
python -m restaurant_orders.benchmark
```

## Тести

```bash
python -m unittest discover -s tests -v
```

## Структура проєкту

```text
restaurant_orders/
├── pyproject.toml
├── README.md
├── .gitignore
├── src/restaurant_orders/
│   ├── __init__.py
│   ├── main.py        # точка входу та консольне меню (ЛР1)
│   ├── models.py      # dataclass Dish і Order
│   ├── services.py    # business logic (ЛР1)
│   ├── data.py        # демонстраційне меню і замовлення (ЛР2)
│   ├── processors.py  # перетворення замовлень у list, set, dict, Counter (ЛР2)
│   ├── analytics.py   # статистика, closure, *args, **kwargs (ЛР2)
│   ├── decorators.py  # measure_time, track_operation, історія deque (ЛР2)
│   ├── analysis.py    # точка входу аналізу (ЛР2)
│   └── benchmark.py   # порівняння пошуку list / dict / set (ЛР2)
└── tests/
    ├── test_services.py
    └── test_analytics.py
```
