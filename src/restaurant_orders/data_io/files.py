"""Own context managers: atomic file writing and a logged operation."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from typing import TextIO

logger = logging.getLogger(__name__)


@contextmanager
def atomic_write(path: Path) -> Iterator[TextIO]:
    """Write into <name>.tmp and replace the target only if the block finished without errors."""
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as file:
            yield file
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def logged_operation(name: str) -> Iterator[None]:
    """Log the start, the duration and the failure of an operation."""
    logger.info("%s: початок", name)
    start = perf_counter()
    try:
        yield
    except Exception:
        logger.error("%s: перервано через помилку", name)
        raise
    else:
        logger.info("%s: завершено за %.4f с", name, perf_counter() - start)
