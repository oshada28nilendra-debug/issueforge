"""Known-correct control fixture; not an automated repair."""

from decimal import Decimal


def total(items):
    return sum((Decimal(str(item)) for item in items), Decimal("0"))
