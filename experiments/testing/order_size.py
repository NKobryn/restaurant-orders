"""Order size classification for the branch coverage experiment of laboratory work 6."""


def classify_order(total: float) -> str:
    """Return the size of an order by its total."""
    if total >= 1000:
        return "large"
    if total >= 300:
        return "medium"
    return "small"
