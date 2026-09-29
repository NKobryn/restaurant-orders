"""FastAPI application: REST API over the orders database.

Run: alembic upgrade head && uvicorn restaurant_orders.api.app:app --reload  (Swagger UI: /docs)
"""

from fastapi import FastAPI

from restaurant_orders import __version__

app = FastAPI(
    title="Restaurant Orders API",
    version=__version__,
    description="REST API обліку замовлень ресторану (лабораторна робота №8, варіант №11).",
)


@app.get("/", tags=["service"])
async def root() -> dict[str, str]:
    """Short information about the service."""
    return {"service": "Restaurant Orders API", "version": __version__, "docs": "/docs"}
