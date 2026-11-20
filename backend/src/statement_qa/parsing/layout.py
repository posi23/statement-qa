"""Rebuild table rows and columns from loose text positions.

A PDF has no table structure, only strings drawn at (x, y). These pure
functions group strings that share a line into rows and match each string to
the column header it sits under.
"""

from typing import Literal, NamedTuple

Column = Literal["date", "description", "debit", "credit", "amount", "balance"]

# Header words seen across statement layouts, mapped to what the column holds.
HEADER_WORDS: dict[str, Column] = {
    "date": "date",
    "description": "description",
    "details": "description",
    "transaction": "description",
    "withdrawals": "debit",
    "debit": "debit",
    "deposits": "credit",
    "credit": "credit",
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


def detect_columns(row: list[TextPiece]) -> dict[Column, float] | None:
    """Return each column's x position if `row` is a table header, else None.

    A header needs a date, a description and a balance column, plus either a
    signed amount column or both debit and credit columns.
    """
    columns: dict[Column, float] = {}
    for piece in row:
        column = HEADER_WORDS.get(piece.text.strip().lower())
        if column is None or column in columns:
            return None
        columns[column] = piece.x
    has_money = "amount" in columns or {"debit", "credit"} <= columns.keys()
    if {"date", "description", "balance"} <= columns.keys() and has_money:
        return columns
    return None


def assign_cells(
    row: list[TextPiece], columns: dict[Column, float]
) -> dict[Column, str]:
    """Put each piece in the column whose header starts nearest to it.

    Nearest start, not "starts after the header", because amounts are
    right-aligned: `80.00` starts well to the right of `Withdrawals` but is
    still much closer to it than to the next header.
    """
    cells: dict[Column, str] = {}
    for piece in row:
        column = min(columns, key=lambda name: abs(columns[name] - piece.x))
        text = piece.text.strip()
        cells[column] = f"{cells[column]} {text}" if column in cells else text
    return cells
