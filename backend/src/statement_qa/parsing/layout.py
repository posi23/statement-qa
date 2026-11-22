"""Rebuild table rows and columns from loose text positions.

A PDF has no table structure, only strings drawn at (x, y). These pure
functions group strings that share a line into rows and match each string to
the column header it sits under.
"""

import re
from typing import Literal, NamedTuple

Column = Literal["date", "description", "debit", "credit", "amount", "balance"]

# Header words seen on statements, mapped to what the column holds. Keys are
# in `normalise_label` form, so `Withdrawals ($)` matches `withdrawals`.
HEADER_WORDS: dict[str, Column] = {
    "date": "date",
    "transaction date": "date",
    "posting date": "date",
    "description": "description",
    "details": "description",
    "transaction": "description",
    "particulars": "description",
    "withdrawals": "debit",
    "withdrawal": "debit",
    "debit": "debit",
    "debits": "debit",
    "money out": "debit",
    "paid out": "debit",
    "deposits": "credit",
    "deposit": "credit",
    "credit": "credit",
    "credits": "credit",
    "money in": "credit",
    "paid in": "credit",
    "amount": "amount",
    "balance": "balance",
}

# Strings drawn on the same line can differ by a fraction of a point.
ROW_TOLERANCE = 2.0


class TextPiece(NamedTuple):
    """A string drawn on a page.

    `x` is where the string starts, in points from the left edge.
    `y` is its baseline, in points from the top edge (so it grows down the page).
    """

    x: float
    y: float
    text: str


class HeaderColumn(NamedTuple):
    """One column of a table header.

    `name` is None for a column we don't use, such as `Ref`. Keeping it still
    matters: values under it go nowhere instead of into a neighbouring column.
    """

    name: Column | None
    x: float


def normalise_label(text: str) -> str:
    """Lowercase, drop anything in brackets and keep only letters and single spaces.

    `Withdrawals ($)` -> `withdrawals`, `Opening Balance:` -> `opening balance`.
    """
    without_units = re.sub(r"\(.*?\)", " ", text.lower())
    letters_only = re.sub(r"[^a-z]+", " ", without_units)
    return " ".join(letters_only.split())


def group_rows(
    pieces: list[TextPiece], tolerance: float = ROW_TOLERANCE
) -> list[list[TextPiece]]:
    """Group pieces into lines, top to bottom, each line sorted left to right."""
    rows: list[list[TextPiece]] = []
    for piece in sorted(pieces, key=lambda p: (p.y, p.x)):
        if rows and abs(piece.y - rows[-1][0].y) <= tolerance:
            rows[-1].append(piece)
        else:
            rows.append([piece])
    return [sorted(row, key=lambda p: p.x) for row in rows]


def detect_columns(row: list[TextPiece]) -> list[HeaderColumn] | None:
    """Return the row's columns if it's a transaction table header, else None.

    A header needs a date, a description and a balance column, plus either a
    signed amount column or both debit and credit columns. Unrecognised words
    become unused columns rather than disqualifying the row.
    """
    columns: list[HeaderColumn] = []
    seen: set[Column] = set()
    for piece in row:
        name = HEADER_WORDS.get(normalise_label(piece.text))
        if name is not None:
            if name in seen:
                return None
            seen.add(name)
        columns.append(HeaderColumn(name=name, x=piece.x))
    has_money = "amount" in seen or {"debit", "credit"} <= seen
    if {"date", "description", "balance"} <= seen and has_money:
        return columns
    return None


def assign_cells(
    row: list[TextPiece], columns: list[HeaderColumn]
) -> dict[Column, str]:
    """Put each piece in the column whose header starts nearest to it.

    Nearest start, not "starts after the header", because amounts are
    right-aligned: `80.00` starts well to the right of `Withdrawals` but is
    still much closer to it than to the next header.
    """
    cells: dict[Column, str] = {}
    for piece in row:
        nearest = min(columns, key=lambda column: abs(column.x - piece.x))
        if nearest.name is None:
            continue
        text = piece.text.strip()
        cells[nearest.name] = (
            f"{cells[nearest.name]} {text}" if nearest.name in cells else text
        )
    return cells
