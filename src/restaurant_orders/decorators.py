"""Decorators that add behaviour to functions without changing their code."""

from collections import deque
from collections.abc import Callable
from functools import wraps
from time import perf_counter
from typing import Any

# Names of the last five analysis operations; older ones drop out automatically.
OPERATION_HISTORY: deque[str] = deque(maxlen=5)


def measure_time(func: Callable[..., Any]) -> Callable[..., Any]:
    """Print how long the decorated function was running."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = perf_counter()
        result = func(*args, **kwargs)
        elapsed = perf_counter() - start
        print(f"[час] {func.__name__}: {elapsed:.4f} с")
        return result

    return wrapper


def track_operation(label: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Remember the label of every call in OPERATION_HISTORY."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            OPERATION_HISTORY.append(label)
            return func(*args, **kwargs)

        return wrapper

    return decorator
