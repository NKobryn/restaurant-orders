"""Plain Python DB-API (sqlite3) access with a parameterized query."""

import sqlite3
from contextlib import closing

FIND_BY_CATEGORY_SQL = """
SELECT dishes.name, dishes.price
FROM dishes
JOIN categories ON categories.id = dishes.category_id
WHERE categories.name = ?
ORDER BY dishes.price DESC, dishes.name
"""


def find_dishes_by_category(database_path: str, category: str) -> list[tuple[str, float]]:
    """Return (name, price) of dishes of a category; the value is passed as a parameter, not glued into SQL."""
    with closing(sqlite3.connect(database_path)) as connection:
        rows = connection.execute(FIND_BY_CATEGORY_SQL, (category,)).fetchall()
    return [(str(name), float(price)) for name, price in rows]
