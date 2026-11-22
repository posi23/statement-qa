"""Turn printed amounts and dates into `Decimal` and `date` values.

Pure functions: no PDF, no I/O, so every format can be tested on a plain string.
"""

import datetime as dt
import re
from decimal import Decimal

_NUMBER = re.compile(r"\d+\.\d{2}")

# Formats that carry their own year, tried in order.
_FULL_DATE_FORMATS = ("%Y-%m-%d", "%d %b %Y", "%b %d, %Y")


def parse_amount(text: str) -> Decimal:
    """Parse a printed amount such as `1,234.56`, `-45.20`, `($45.20)` or `45.20 OD`.

    Parentheses, a leading minus and an `OD` (overdrawn) suffix all mean negative.

    Raises:
        ValueError: if the text isn't an amount with exactly two decimal places.
    """
    cleaned = text.strip()
    negative = False
    if cleaned.upper().endswith(" OD"):
        negative = True
        cleaned = cleaned[:-3].strip()
    if cleaned.startswith("(") and cleaned.endswith(")"):
        negative = True
        cleaned = cleaned[1:-1].strip()
    if cleaned.startswith("-"):
        negative = True
        cleaned = cleaned[1:].strip()
    cleaned = cleaned.removeprefix("$").replace(",", "")
    if not _NUMBER.fullmatch(cleaned):
        raise ValueError(f"not an amount: {text!r}")
    value = Decimal(cleaned)
    return -value if negative else value


def parse_full_date(text: str) -> dt.date:
    """Parse a date with its year: `2026-03-04`, `04 Mar 2026` or `Mar 04, 2026`.

    Raises:
        ValueError: if no known format matches.
    """
    cleaned = text.strip()
    for date_format in _FULL_DATE_FORMATS:
        try:
            return dt.datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue
    raise ValueError(f"not a date: {text!r}")


def parse_row_date(text: str, period_start: dt.date, period_end: dt.date) -> dt.date:
    """Parse a transaction date, taking the year from the statement period if needed.

    `Jan 03` on a Dec 15 to Jan 14 statement belongs to the later year, so the
    year is whichever one puts the date inside the period.

    Raises:
        ValueError: if the text isn't a date, or a year-less date is outside the
            period.
    """
    try:
        return parse_full_date(text)
    except ValueError:
        pass
    cleaned = text.strip()
    for year in sorted({period_start.year, period_end.year}):
        try:
            candidate = dt.datetime.strptime(f"{cleaned} {year}", "%b %d %Y").date()
        except ValueError:
            # `Feb 29` is valid in some years only, so try the other year.
            continue
        if period_start <= candidate <= period_end:
            return candidate
    raise ValueError(f"not a date in {period_start}..{period_end}: {text!r}")
