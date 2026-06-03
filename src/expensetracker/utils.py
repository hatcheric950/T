from __future__ import annotations
from datetime import date
from typing import Union


_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]


def format_currency(amount: float, symbol: str = "$") -> str:
    """Return a human-readable currency string, e.g. '$1,234.56'."""
    if not isinstance(amount, (int, float)):
        raise TypeError(f"amount must be a number, got {type(amount).__name__!r}")
    return f"{symbol}{amount:,.2f}"


def parse_date(date_str: str) -> date:
    """Parse a date string in several common formats and return a date object."""
    if not isinstance(date_str, str):
        raise TypeError(f"date_str must be a string, got {type(date_str).__name__!r}")
    for fmt in _DATE_FORMATS:
        try:
            return date.fromisoformat(date_str) if fmt == "%Y-%m-%d" else _strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(
        f"date_str {date_str!r} does not match any supported format: "
        f"{_DATE_FORMATS}"
    )


def _strptime(date_str: str, fmt: str) -> date:
    from datetime import datetime
    return datetime.strptime(date_str, fmt).date()


def validate_positive(value: Union[int, float], name: str) -> None:
    """Raise ValueError with a descriptive message if value is not positive."""
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
