"""Immutable value objects of the restaurant domain."""

from dataclasses import dataclass
from functools import total_ordering

from restaurant_orders.domain.exceptions import CurrencyMismatchError


@total_ordering
@dataclass(frozen=True, slots=True)
class Money:
    """Amount of money in one currency; cannot be changed after creation."""

    amount: float
    currency: str = "UAH"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Сума грошей не може бути від'ємною.")
        if not self.currency:
            raise ValueError("Валюта має бути вказана.")

    def _check_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(f"Різні валюти: {self.currency} і {other.currency}.")

    def __add__(self, other: "Money") -> "Money":
        self._check_currency(other)
        return Money(round(self.amount + other.amount, 2), self.currency)

    def __mul__(self, quantity: int) -> "Money":
        return Money(round(self.amount * quantity, 2), self.currency)

    def __lt__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount < other.amount

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"
