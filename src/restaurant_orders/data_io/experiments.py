"""Experiments of laboratory work 5: policies, streaming, chaining, atomic output, configuration errors."""

import csv
import logging
import os
import sys
import tempfile
import traceback
import tracemalloc
from collections.abc import Callable, Iterator
from pathlib import Path
from time import perf_counter
from typing import Any

from restaurant_orders.data_io.config import AppConfig, LoggingConfig, ValidationRules, load_config
from restaurant_orders.data_io.exceptions import ApplicationError, DataExportError, RecordValidationError
from restaurant_orders.data_io.exporters import export_json
from restaurant_orders.data_io.files import logged_operation
from restaurant_orders.data_io.readers import FIELDS, CsvImporter
from restaurant_orders.data_io.services import ImportStatistics, run_import, valid_records
from restaurant_orders.data_io.validators import validate_row
from restaurant_orders.models import OrderItemRecord
from restaurant_orders.stream.dataset import ensure_dataset

RULES = ValidationRules(frozenset({"Перші страви", "Основні страви", "Десерти", "Напої"}), 20.0, 500.0)
SIZES: tuple[int, ...] = (10_000, 100_000, 500_000)
REPEATS = 3


def make_config(folder: Path, input_path: Path, skip_invalid: bool) -> AppConfig:
    """Build a configuration object for an experiment without a YAML file."""
    return AppConfig(
        input_path=input_path,
        output_path=folder / "orders.json",
        errors_path=folder / "invalid.csv",
        summary_path=folder / "summary.json",
        skip_invalid=skip_invalid,
        rules=RULES,
        logging=LoggingConfig("INFO", folder / "import.log"),
    )


def write_policy_dataset(path: Path) -> None:
    """Write 1000 valid rows and 10 rows with a negative quantity (every 101st row)."""
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(FIELDS)
        for number in range(1, 1011):
            quantity = -1 if number % 101 == 0 else 1
            writer.writerow([number, "Борщ", "Перші страви", "95.00", quantity])


def policies_experiment(folder: Path) -> None:
    """Experiment 1: the same file in strict and tolerant mode."""
    print("\nЕКСПЕРИМЕНТ 1. STRICT ПРОТИ TOLERANT (1000 коректних + 10 некоректних рядків)")
    input_path = folder / "policy.csv"
    write_policy_dataset(input_path)
    results = {}
    for mode, skip_invalid in (("strict", False), ("tolerant", True)):
        statistics = ImportStatistics()
        try:
            run_import(make_config(folder / mode, input_path, skip_invalid), statistics)
            finish = "успішно, код 0"
        except ApplicationError as error:
            finish = f"зупинка: {error}"
        results[mode] = (statistics, finish)
    print(f"{'Параметр':<18} | {'strict':>8} | {'tolerant':>8}")
    print("-" * 40)
    for title, name in (("Оброблено записів", "total"), ("Valid", "valid"), ("Invalid", "invalid"),
                        ("Exported", "exported")):
        print(f"{title:<18} | {getattr(results['strict'][0], name):>8} | {getattr(results['tolerant'][0], name):>8}")
    for mode in ("strict", "tolerant"):
        print(f"Завершення {mode}: {results[mode][1]}")


def eager_import(path: Path) -> list[OrderItemRecord]:
    """Eager: read all rows into a list, then validate all of them into another list."""
    rows = list(CsvImporter().read(path))
    records = []
    for line_number, row in rows:
        try:
            records.append(validate_row(line_number, row, RULES))
        except RecordValidationError:
            continue
    return records


def streaming_import(path: Path) -> int:
    """Streaming: rows flow through the generator pipeline one by one."""
    config = make_config(path.parent, path, skip_invalid=True)
    return sum(1 for _ in valid_records(config, ImportStatistics(), lambda error: None))


def best_time(action: Callable[[], Any]) -> float:
    """Return the best of REPEATS runs in seconds."""
    times = []
    for _ in range(REPEATS):
        start = perf_counter()
        action()
        times.append(perf_counter() - start)
    return min(times)


def peak_mb(action: Callable[[], Any]) -> float:
    """Return peak memory allocated during the action in megabytes."""
    tracemalloc.start()
    action()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / 1024 / 1024


def streaming_experiment(datasets: dict[int, Path]) -> None:
    """Experiment 2: eager and streaming import of large files."""
    print("\nЕКСПЕРИМЕНТ 2. STREAMING ПРОТИ EAGER (import + validation, ~1 % некоректних рядків)")
    print(f"Час: найкращий із {REPEATS}; пам'ять: пік tracemalloc")
    print(f"{'Записів':>8} | {'валідних':>8} | {'eager, с':>8} | {'stream, с':>9} | {'eager, МБ':>9} | {'stream, МБ':>10}")
    print("-" * 70)
    logging.disable(logging.WARNING)
    for size, path in datasets.items():
        valid = streaming_import(path)
        if len(eager_import(path)) != valid:
            raise RuntimeError("eager і streaming дали різну кількість записів")
        print(f"{size:>8} | {valid:>8} | {best_time(lambda: eager_import(path)):>8.3f} | "
              f"{best_time(lambda: streaming_import(path)):>9.3f} | {peak_mb(lambda: eager_import(path)):>9.2f} | "
              f"{peak_mb(lambda: streaming_import(path)):>10.2f}")
    logging.disable(logging.NOTSET)


def chaining_experiment(project: Path) -> None:
    """Experiment 3: traceback of ValueError -> RecordValidationError."""
    print("\nЕКСПЕРИМЕНТ 3. EXCEPTION CHAINING (рядок: 1,Борщ,Перші страви,wrong,1)")
    row = {"order_id": "1", "dish": "Борщ", "category": "Перші страви", "price": "wrong", "quantity": "1"}
    try:
        validate_row(2, row, RULES)
    except RecordValidationError as error:
        root = str(project) + "/"
        print("".join(traceback.format_exception(error)).replace(root, ""), end="")
        print(f"error.__cause__ = {error.__cause__!r}")


def failing_records() -> Iterator[OrderItemRecord]:
    """Yield two records and then simulate a disk error."""
    yield OrderItemRecord(1, "Борщ", "Перші страви", 95.0, 1)
    yield OrderItemRecord(2, "Узвар", "Напої", 45.0, 2)
    raise OSError(28, "No space left on device")


def atomic_experiment(folder: Path) -> None:
    """Experiment 4: an error during export keeps the previous output."""
    print("\nЕКСПЕРИМЕНТ 4. ATOMIC OUTPUT (помилка диска посередині export)")
    output = folder / "atomic.json"
    export_json([OrderItemRecord(7, "Стейк", "Основні страви", 280.0, 1)], output)
    before = output.read_text(encoding="utf-8")
    try:
        with logged_operation("Експорт з імітацією збою"):
            export_json(failing_records(), output)
    except DataExportError as error:
        print(f"Перехоплено: {type(error).__name__}: {error} (причина: {error.__cause__!r})")
    print(f"Попередній output не змінився: {output.read_text(encoding='utf-8') == before}")
    print(f"Тимчасовий файл існує: {(folder / 'atomic.json.tmp').exists()}")
    print(f"Файли в каталозі: {sorted(path.name for path in folder.iterdir() if path.suffix in {'.json', '.tmp'})}")


VALID_YAML = """schema_version: 1
input: {path: INPUT}
output: {path: OUT/orders.json, errors_path: OUT/invalid.csv, summary_path: OUT/summary.json}
processing:
  skip_invalid: true
  allowed_categories: [Напої]
  price_range: {min: 20, max: 500}
logging: {level: INFO, path: OUT/import.log}
"""


def configuration_experiment(folder: Path) -> None:
    """Experiment 5: typical configuration mistakes."""
    print("\nЕКСПЕРИМЕНТ 5. ПОМИЛКИ КОНФІГУРАЦІЇ")
    data = folder / "input.csv"
    data.write_text(",".join(FIELDS) + "\n", encoding="utf-8")
    good = VALID_YAML.replace("INPUT", str(data)).replace("OUT", str(folder))
    cases = {
        "відсутній config.yaml": None,
        "неправильний YAML": good.replace("processing:", "processing: [", 1),
        "немає ключа input": good.replace(f"input: {{path: {data}}}\n", ""),
        "price_range max = -5": good.replace("max: 500", "max: -5"),
        "input file відсутній": good.replace(str(data), str(folder / "missing.csv")),
        "output directory не існує": good.replace(f"{folder}/orders.json", f"{folder}/nope/orders.json"),
    }
    for number, (title, text) in enumerate(cases.items(), start=1):
        path = folder / f"config_{number}.yaml"
        if text is not None:
            path.write_text(text, encoding="utf-8")
        try:
            load_config(path)
            result = "помилки немає"
        except ApplicationError as error:
            cause = f" (причина: {type(error.__cause__).__name__})" if error.__cause__ else ""
            result = f"{type(error).__name__}: {error}{cause}"
        print(f"{number}. {title}: {result}")


def main() -> None:
    """Run all experiments in a temporary working folder."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s", stream=sys.stdout, force=True)
    print("ЕКСПЕРИМЕНТИ ЛАБОРАТОРНОЇ РОБОТИ №5")
    project = Path.cwd()
    datasets = {size: ensure_dataset(size).resolve() for size in SIZES}
    with tempfile.TemporaryDirectory() as name:
        os.chdir(name)
        try:
            folder = Path("exp")
            for mode in ("strict", "tolerant"):
                (folder / mode).mkdir(parents=True)
            logging.disable(logging.INFO)
            policies_experiment(folder)
            logging.disable(logging.NOTSET)
            streaming_experiment(datasets)
            chaining_experiment(project)
            atomic_experiment(folder)
            configuration_experiment(folder)
        finally:
            os.chdir(project)


if __name__ == "__main__":
    main()
