# Stage 1: build the wheel of restaurant-orders
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir build && python -m build --wheel

# Stage 2: runtime image with the installed wheel only
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    HOST=0.0.0.0 \
    PORT=8000 \
    DATABASE_URL=sqlite:////app/data/restaurant.db
COPY --from=builder /build/dist/*.whl /tmp/
RUN python -m pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl
# Alembic migrations are applied by restaurant-orders at start (alembic.ini is found in /app)
COPY alembic.ini ./
COPY migrations ./migrations
RUN useradd --create-home appuser && mkdir -p /app/data && chown appuser /app/data
USER appuser
VOLUME ["/app/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["restaurant-orders"]
