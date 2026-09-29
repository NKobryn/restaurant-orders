"""FastAPI application: REST API over the orders database.

Run: restaurant-orders (or alembic upgrade head && uvicorn restaurant_orders.api.app:app --reload); Swagger UI: /docs
"""

import logging
from http import HTTPStatus
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from restaurant_orders import __version__
from restaurant_orders.api.dependencies import get_session
from restaurant_orders.api.schemas import (
    CategoryResponse,
    CategoryStatisticsResponse,
    DishCreate,
    DishResponse,
    DishUpdate,
    ErrorResponse,
    OrderCreate,
    OrderItemCreate,
    OrderItemResponse,
    OrderResponse,
    OrderStatisticsResponse,
    OrderTotalResponse,
)
from restaurant_orders.config import get_settings
from restaurant_orders.persistence.models import Dish, Order
from restaurant_orders.persistence.repositories import CategoryRepository, DishRepository, OrderRepository
from restaurant_orders.persistence.services import OrderPlacementError, OrderService, UnknownDishError

logger = logging.getLogger(__name__)

app = FastAPI(
    title=get_settings().app_name,
    version=__version__,
    description="REST API обліку замовлень ресторану (варіант №11): меню, замовлення, суми, статистика.",
    openapi_tags=[
        {"name": "dishes", "description": "Меню: страви та категорії"},
        {"name": "orders", "description": "Замовлення, позиції, суми та статистика"},
    ],
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)

SessionDep = Annotated[Session, Depends(get_session)]


def error_response(code: int, detail: str) -> JSONResponse:
    """Structured JSON error: status code, its name and a human-readable detail."""
    body = ErrorResponse(status=code, error=HTTPStatus(code).phrase, detail=detail)
    return JSONResponse(status_code=code, content=body.model_dump())


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, error: HTTPException) -> JSONResponse:
    return error_response(error.status_code, str(error.detail))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    problems = "; ".join(f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}" for item in error.errors())
    return error_response(status.HTTP_422_UNPROCESSABLE_CONTENT, problems)


@app.exception_handler(UnknownDishError)
async def unknown_dish_handler(request: Request, error: UnknownDishError) -> JSONResponse:
    return error_response(status.HTTP_404_NOT_FOUND, str(error))


@app.exception_handler(OrderPlacementError)
async def order_error_handler(request: Request, error: OrderPlacementError) -> JSONResponse:
    logger.warning("Order rejected: %s", error)
    return error_response(status.HTTP_409_CONFLICT, str(error))


def get_dish_or_404(session: Session, dish_id: int) -> Dish:
    dish = DishRepository(session).get(dish_id)
    if dish is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Страву #{dish_id} не знайдено.")
    return dish


def get_order_or_404(session: Session, order_id: int) -> Order:
    order = OrderRepository(session).get(order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Замовлення №{order_id} не знайдено.")
    return order


@app.get("/", tags=["service"])
async def root() -> dict[str, str]:
    """Short information about the service."""
    return {"service": get_settings().app_name, "version": __version__, "docs": "/docs"}


@app.get("/health", tags=["service"])
async def health() -> dict[str, str]:
    """Health check for Docker and monitoring: the service is running."""
    return {"status": "ok", "environment": get_settings().environment}


# --- dishes and categories ---


@app.get("/categories", tags=["dishes"])
async def list_categories(session: SessionDep) -> list[CategoryResponse]:
    """All categories with the number of dishes."""
    return [
        CategoryResponse(id=category.id, name=category.name, dishes_count=count)
        for category, count in CategoryRepository(session).list_with_counts()
    ]


@app.get("/dishes", tags=["dishes"])
async def list_dishes(
    session: SessionDep,
    category: str | None = None,
    sort: Literal["price_desc", "price_asc", "name"] = "price_desc",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DishResponse]:
    """Menu with filtering by category, sorting and pagination (query parameters)."""
    dishes = DishRepository(session).list(category=category, limit=limit, offset=offset, sort=sort)
    return [DishResponse.from_model(dish) for dish in dishes]


@app.get("/dishes/{dish_id}", tags=["dishes"])
async def get_dish(dish_id: int, session: SessionDep) -> DishResponse:
    """One dish by its id (path parameter)."""
    return DishResponse.from_model(get_dish_or_404(session, dish_id))


@app.post("/dishes", status_code=status.HTTP_201_CREATED, tags=["dishes"])
async def create_dish(data: DishCreate, session: SessionDep) -> DishResponse:
    """Add a dish to the menu; the category is created when needed."""
    category = CategoryRepository(session).get_or_create(data.category)
    try:
        dish = DishRepository(session).add(data.name, category, data.price)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, f"Страва «{data.name}» вже є в меню.") from None
    return DishResponse.from_model(dish)


@app.patch("/dishes/{dish_id}", tags=["dishes"])
async def update_dish(dish_id: int, data: DishUpdate, session: SessionDep) -> DishResponse:
    """Change the price and/or the category of a dish."""
    dish = get_dish_or_404(session, dish_id)
    if data.price is not None:
        dish.price = data.price
    if data.category is not None:
        dish.category = CategoryRepository(session).get_or_create(data.category)
    session.commit()
    return DishResponse.from_model(dish)


@app.delete("/dishes/{dish_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["dishes"])
async def delete_dish(dish_id: int, session: SessionDep) -> None:
    """Delete a dish that is not used in any order."""
    get_dish_or_404(session, dish_id)
    try:
        DishRepository(session).delete(dish_id)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, f"Страва #{dish_id} є в замовленнях.") from None


# --- orders ---


@app.get("/orders", tags=["orders"])
async def list_orders(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[OrderResponse]:
    """History of orders (oldest first), page by page."""
    service = OrderService(session)
    return [
        OrderResponse.from_model(order, service.most_expensive_item(order.id))
        for order in OrderRepository(session).history(limit=limit, offset=offset)
    ]


@app.post("/orders", status_code=status.HTTP_201_CREATED, tags=["orders"])
async def create_order(data: OrderCreate, session: SessionDep) -> OrderResponse:
    """Create an order with all its items in one transaction."""
    service = OrderService(session)
    order = service.place_order(data.id, [(item.dish, item.quantity) for item in data.items])
    logger.info("Order %s created with %s items", order.id, len(data.items))
    return OrderResponse.from_model(order, service.most_expensive_item(order.id))


@app.get("/orders/statistics", tags=["orders"])
async def order_statistics(session: SessionDep) -> OrderStatisticsResponse:
    """Number of orders, average order value and revenue by category."""
    service = OrderService(session)
    return OrderStatisticsResponse(
        orders_count=OrderRepository(session).count(),
        average_order_value=service.average_order_value(),
        categories=[
            CategoryStatisticsResponse(category=row.category, portions=row.portions, revenue=row.revenue)
            for row in service.category_statistics()
        ],
    )


@app.get("/orders/{order_id}", tags=["orders"])
async def get_order(order_id: int, session: SessionDep) -> OrderResponse:
    """One order with its items, total and the most expensive position."""
    order = get_order_or_404(session, order_id)
    return OrderResponse.from_model(order, OrderService(session).most_expensive_item(order_id))


@app.post("/orders/{order_id}/items", status_code=status.HTTP_201_CREATED, tags=["orders"])
async def add_order_item(order_id: int, data: OrderItemCreate, session: SessionDep) -> OrderItemResponse:
    """Add a dish to an existing order."""
    get_order_or_404(session, order_id)
    return OrderItemResponse.from_model(OrderService(session).add_dish(order_id, data.dish, data.quantity))


@app.delete("/orders/{order_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["orders"])
async def delete_order_item(order_id: int, item_id: int, session: SessionDep) -> None:
    """Remove one position from an order."""
    get_order_or_404(session, order_id)
    if not OrderService(session).remove_item(order_id, item_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"У замовленні №{order_id} немає позиції #{item_id}.")


@app.get("/orders/{order_id}/total", tags=["orders"])
async def get_order_total(order_id: int, session: SessionDep) -> OrderTotalResponse:
    """Total of an order computed by SQL SUM."""
    order = get_order_or_404(session, order_id)
    return OrderTotalResponse(
        order_id=order_id, items_count=len(order.items), total=OrderService(session).order_total(order_id)
    )
