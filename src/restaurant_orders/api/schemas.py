"""Pydantic schemas: JSON bodies of requests and responses with validation rules."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from restaurant_orders.persistence.models import Dish, Order, OrderItem


class ApiModel(BaseModel):
    """Base schema: extra fields are rejected, text is stripped."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ErrorResponse(ApiModel):
    """Structured error returned by every failed request."""

    status: int
    error: str
    detail: str


class DishCreate(ApiModel):
    """Body of POST /dishes."""

    name: str = Field(min_length=1, max_length=100, examples=["Борщ"])
    category: str = Field(min_length=1, max_length=50, examples=["Перші страви"])
    price: float = Field(gt=0, le=10_000, examples=[95.0])


class DishUpdate(ApiModel):
    """Body of PATCH /dishes/{dish_id}: only the given fields change."""

    price: float | None = Field(default=None, gt=0, le=10_000)
    category: str | None = Field(default=None, min_length=1, max_length=50)


class DishResponse(ApiModel):
    """Dish as returned by the API."""

    id: int
    name: str
    category: str
    price: float

    @classmethod
    def from_model(cls, dish: Dish) -> "DishResponse":
        return cls(id=dish.id, name=dish.name, category=dish.category.name, price=dish.price)


class CategoryResponse(ApiModel):
    """Category with the number of its dishes."""

    id: int
    name: str
    dishes_count: int


class OrderItemCreate(ApiModel):
    """One position of a new order: dish name and quantity."""

    dish: str = Field(min_length=1, max_length=100, examples=["Борщ"])
    quantity: int = Field(default=1, gt=0, le=100)


class OrderCreate(ApiModel):
    """Body of POST /orders."""

    id: int = Field(gt=0, examples=[101])
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItemResponse(ApiModel):
    """Position of an order."""

    id: int
    dish: str
    quantity: int
    unit_price: float
    line_total: float

    @classmethod
    def from_model(cls, item: OrderItem) -> "OrderItemResponse":
        return cls(id=item.id, dish=item.dish.name, quantity=item.quantity, unit_price=item.unit_price,
                   line_total=item.line_total)


class OrderResponse(ApiModel):
    """Order with items, total and the most expensive position."""

    id: int
    created_at: datetime
    items: list[OrderItemResponse]
    total: float
    most_expensive: OrderItemResponse | None

    @classmethod
    def from_model(cls, order: Order, most_expensive: OrderItem | None) -> "OrderResponse":
        return cls(
            id=order.id,
            created_at=order.created_at,
            items=[OrderItemResponse.from_model(item) for item in order.items],
            total=order.total,
            most_expensive=None if most_expensive is None else OrderItemResponse.from_model(most_expensive),
        )


class OrderTotalResponse(ApiModel):
    """Answer of GET /orders/{order_id}/total."""

    order_id: int
    items_count: int
    total: float


class CategoryStatisticsResponse(ApiModel):
    """Portions and revenue of one category."""

    category: str
    portions: int
    revenue: float


class OrderStatisticsResponse(ApiModel):
    """Answer of GET /orders/statistics."""

    orders_count: int
    average_order_value: float
    categories: list[CategoryStatisticsResponse]
