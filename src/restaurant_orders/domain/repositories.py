"""Abstract and in-memory generic repositories."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from restaurant_orders.domain.protocols import HasId

T = TypeVar("T", bound=HasId)


class Repository(ABC, Generic[T]):
    """Storage of objects of one type T with access by id."""

    @abstractmethod
    def add(self, item: T) -> None:
        """Save an item (replace an item with the same id)."""

    @abstractmethod
    def get(self, item_id: int) -> T | None:
        """Return the item with the id or None."""

    @abstractmethod
    def all(self) -> list[T]:
        """Return all stored items."""


class InMemoryRepository(Repository[T]):
    """Repository that keeps items in a dictionary in memory."""

    def __init__(self) -> None:
        self._items: dict[int, T] = {}

    def add(self, item: T) -> None:
        self._items[item.id] = item

    def get(self, item_id: int) -> T | None:
        return self._items.get(item_id)

    def all(self) -> list[T]:
        return list(self._items.values())

    def __len__(self) -> int:
        return len(self._items)
