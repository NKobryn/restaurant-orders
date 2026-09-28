"""Pricing strategies: how the final order total is calculated."""

from abc import ABC, abstractmethod

from restaurant_orders.domain.models import Order
from restaurant_orders.domain.value_objects import Money


class PricingPolicy(ABC):
    """Base class for rules that turn an order into the amount to pay."""

    @abstractmethod
    def final_total(self, order: Order) -> Money:
        """Return the amount the guest has to pay for the order."""


class NoDiscount(PricingPolicy):
    """The guest pays the full order total."""

    def final_total(self, order: Order) -> Money:
        return order.total


class CategoryDiscount(PricingPolicy):
    """Percentage discount for dishes of one category (for example, happy hour drinks)."""

    def __init__(self, category: str, percent: float) -> None:
        if not 0 < percent <= 100:
            raise ValueError("Знижка має бути від 0 до 100 %.")
        self.category = category
        self.percent = percent

    def final_total(self, order: Order) -> Money:
        total = Money(0)
        for item in order:
            price = item.total
            if item.dish.category == self.category:
                price = Money(round(price.amount * (1 - self.percent / 100), 2), price.currency)
            total = total + price
        return total
