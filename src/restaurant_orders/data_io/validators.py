"""Validation of one input record according to the configured rules."""

from restaurant_orders.data_io.config import ValidationRules
from restaurant_orders.data_io.exceptions import RecordValidationError
from restaurant_orders.data_io.readers import FIELDS, Row
from restaurant_orders.models import OrderItemRecord


def to_int(row: Row, field: str, line_number: int) -> int:
    """Convert a field to int or raise RecordValidationError with the original cause."""
    try:
        return int(str(row[field]))
    except ValueError as error:
        raise RecordValidationError(
            f"{row[field]!r} не є цілим числом.", line_number=line_number, field=field
        ) from error


def to_float(row: Row, field: str, line_number: int) -> float:
    """Convert a field to float or raise RecordValidationError with the original cause."""
    try:
        return float(str(row[field]))
    except ValueError as error:
        raise RecordValidationError(f"{row[field]!r} не є числом.", line_number=line_number, field=field) from error


def validate_row(line_number: int, row: Row, rules: ValidationRules) -> OrderItemRecord:
    """Turn one raw record into a checked OrderItemRecord."""
    if None in row:
        raise RecordValidationError("Забагато полів у записі.", line_number=line_number)
    for field in FIELDS:
        if row.get(field) is None:
            raise RecordValidationError("Поле відсутнє.", line_number=line_number, field=field)

    order_id = to_int(row, "order_id", line_number)
    dish = str(row["dish"]).strip()
    category = str(row["category"]).strip()
    price = to_float(row, "price", line_number)
    quantity = to_int(row, "quantity", line_number)

    if order_id <= 0:
        raise RecordValidationError("Номер замовлення має бути додатним.", line_number=line_number, field="order_id")
    if not dish:
        raise RecordValidationError("Назва страви порожня.", line_number=line_number, field="dish")
    if quantity <= 0:
        raise RecordValidationError("Кількість має бути більшою за нуль.", line_number=line_number, field="quantity")
    if category not in rules.allowed_categories:
        raise RecordValidationError(f"Категорія «{category}» не дозволена.", line_number=line_number, field="category")
    if not rules.min_price <= price <= rules.max_price:
        raise RecordValidationError(
            f"Ціна {price:.2f} поза діапазоном {rules.min_price:.2f}–{rules.max_price:.2f}.",
            line_number=line_number,
            field="price",
        )
    try:
        return OrderItemRecord(order_id, dish, category, price, quantity)
    except ValueError as error:
        raise RecordValidationError(str(error), line_number=line_number) from error
