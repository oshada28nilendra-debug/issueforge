"""Intentionally buggy fixture, authored for IssueForge; not third-party code."""

from decimal import Decimal


def total(items):
    """Return the exact decimal sum of currency amounts."""
    return Decimal(str(sum(float(item) for item in items)))
