# Restaurant Orders

Лабораторна робота №1 з курсу «Професійний Python».

Варіант №11 — «Облік замовлень ресторану».

## Можливості

- створення замовлень і додавання страв;
- підрахунок суми кожного замовлення;
- пошук найдорожчої позиції в замовленні;
- обчислення середньої вартості замовлень;
- сортування замовлень за сумою;
- інтерактивне меню з перевіркою введених даних.

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
│   ├── main.py       # точка входу та консольне меню
│   ├── models.py     # dataclass Dish і Order
│   └── services.py   # business logic
└── tests/test_services.py
```
