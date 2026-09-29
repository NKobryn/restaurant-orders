"""Design experiments: dependency injection and inheritance versus composition."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Protocol

from restaurant_orders.domain.adapters import DemoPaymentGateway, LimitedPaymentGateway
from restaurant_orders.domain.exceptions import PaymentError
from restaurant_orders.domain.models import Dish, Order
from restaurant_orders.domain.protocols import PaymentGateway
from restaurant_orders.domain.value_objects import Money

MENU_LINES = ["1,Борщ,Перші страви,95", "5;Стейк;Основні страви;280", "8,Узвар,Напої,45", "9,Капучино,Напої,-75"]


# --- Experiment 1: the service creates its dependency (A) or receives it (B) ---


class HardwiredCheckout:
    """Variant A: the service creates a concrete payment gateway itself."""

    def __init__(self) -> None:
        self._gateway = DemoPaymentGateway()

    def pay(self, order: Order) -> str:
        return self._gateway.pay(order.id, order.total)


class InjectedCheckout:
    """Variant B: any object that follows PaymentGateway is passed in."""

    def __init__(self, gateway: PaymentGateway) -> None:
        self._gateway = gateway

    def pay(self, order: Order) -> str:
        return self._gateway.pay(order.id, order.total)


class RecordingGateway:
    """Fake gateway for tests: remembers payments instead of charging money."""

    def __init__(self) -> None:
        self.payments: list[tuple[int, Money]] = []

    def pay(self, order_id: int, amount: Money) -> str:
        self.payments.append((order_id, amount))
        return f"TEST-{order_id}"


# --- Experiment 2: the same behaviour through inheritance and composition ---


def to_dish(fields: list[str]) -> Dish:
    """Create a dish from four text fields: id, name, category, price."""
    return Dish(int(fields[0]), fields[1], fields[2], Money(float(fields[3])))


class BaseMenuImporter(ABC):
    """Inheritance: the base class fixes the algorithm, subclasses change one step."""

    def import_dishes(self, lines: Iterable[str]) -> list[Dish]:
        dishes = []
        for line in lines:
            fields = self.parse(line)
            if len(fields) == 4 and self.is_valid(fields):
                dishes.append(to_dish(fields))
        return dishes

    @abstractmethod
    def parse(self, line: str) -> list[str]:
        """Split one line into fields."""

    def is_valid(self, fields: list[str]) -> bool:
        """Accept dishes with a positive price."""
        return float(fields[3]) > 0


class CommaMenuImporter(BaseMenuImporter):
    """Importer for lines separated by commas."""

    def parse(self, line: str) -> list[str]:
        return line.split(",")


class SemicolonMenuImporter(BaseMenuImporter):
    """Importer for lines separated by semicolons."""

    def parse(self, line: str) -> list[str]:
        return line.split(";")


class LineParser(Protocol):
    """Splits one line into fields."""

    def parse(self, line: str) -> list[str]: ...


class FieldsValidator(Protocol):
    """Decides whether the fields describe a correct dish."""

    def is_valid(self, fields: list[str]) -> bool: ...


class SeparatorParser:
    """Parser for any separator character."""

    def __init__(self, separator: str) -> None:
        self.separator = separator

    def parse(self, line: str) -> list[str]:
        return line.split(self.separator)


class AnySeparatorParser:
    """Parser that accepts both commas and semicolons."""

    def parse(self, line: str) -> list[str]:
        return line.replace(";", ",").split(",")


class PositivePriceValidator:
    """Accepts only dishes with a positive price."""

    def is_valid(self, fields: list[str]) -> bool:
        return float(fields[3]) > 0


class MenuImporter:
    """Composition: the importer has a parser and a validator and delegates work to them."""

    def __init__(self, parser: LineParser, validator: FieldsValidator) -> None:
        self.parser = parser
        self.validator = validator

    def import_dishes(self, lines: Iterable[str]) -> list[Dish]:
        dishes = []
        for line in lines:
            fields = self.parser.parse(line)
            if len(fields) == 4 and self.validator.is_valid(fields):
                dishes.append(to_dish(fields))
        return dishes


def names(dishes: list[Dish]) -> str:
    """Join dish names for printing."""
    return ", ".join(dish.name for dish in dishes) or "—"


def main() -> None:
    """Run both experiments and print what each design allows."""
    order = Order(7)
    order.add_dish(Dish(5, "Стейк", "Основні страви", Money(280.0)), 2)
    print("ЕКСПЕРИМЕНТ 1. Сервіс сам створює gateway (A) проти dependency injection (B)")
    print(f"Замовлення №{order.id}: {order.total}")
    print("A. HardwiredCheckout — завжди справжній DemoPaymentGateway:")
    HardwiredCheckout().pay(order)
    print("B. InjectedCheckout з трьома різними gateway без зміни коду сервісу:")
    recorder = RecordingGateway()
    print(
        f"  RecordingGateway (fake для тесту) -> {InjectedCheckout(recorder).pay(order)}, "
        f"записано: {[(number, str(amount)) for number, amount in recorder.payments]}"
    )
    print(f"  DemoPaymentGateway -> {InjectedCheckout(DemoPaymentGateway()).pay(order)}")
    try:
        InjectedCheckout(LimitedPaymentGateway(Money(500.0))).pay(order)
    except PaymentError as error:
        print(f"  LimitedPaymentGateway(500) -> PaymentError: {error}")

    print("\nЕКСПЕРИМЕНТ 2. Імпорт меню: inheritance проти composition")
    print(f"Рядки: {MENU_LINES}")
    print(f"Inheritance, CommaMenuImporter:      {names(CommaMenuImporter().import_dishes(MENU_LINES))}")
    print(f"Inheritance, SemicolonMenuImporter:  {names(SemicolonMenuImporter().import_dishes(MENU_LINES))}")
    comma = MenuImporter(SeparatorParser(","), PositivePriceValidator())
    both = MenuImporter(AnySeparatorParser(), PositivePriceValidator())
    print(f"Composition, SeparatorParser(','):   {names(comma.import_dishes(MENU_LINES))}")
    print(f"Composition, AnySeparatorParser():   {names(both.import_dishes(MENU_LINES))}")
    print("Для формату «кома або крапка з комою» inheritance потребує нового підкласу,")
    print("composition — лише іншого parser у конструкторі; validator використовується повторно.")


if __name__ == "__main__":
    main()
