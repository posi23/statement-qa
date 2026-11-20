"""Tests for rebuilding rows and columns from text positions."""

import pytest

from statement_qa.parsing.layout import (
    Column,
    TextPiece,
    assign_cells,
    detect_columns,
    group_rows,
)

# Header x positions as pypdf reports them for layout A.
LAYOUT_A: dict[Column, float] = {
    "date": 42.8,
    "description": 117.8,
    "debit": 328.2,
    "credit": 426.0,
    "balance": 535.0,
}


def header(*words: str) -> list[TextPiece]:
    """A header row with one word every 100pt."""
    return [TextPiece(x=40 + i * 100, y=160, text=w) for i, w in enumerate(words)]


@pytest.mark.parametrize(
    ("words", "expected"),
    [
        (
            ("Date", "Description", "Withdrawals", "Deposits", "Balance"),
            {"date", "description", "debit", "credit", "balance"},
        ),
        (
            ("Date", "Details", "Amount", "Balance"),
            {"date", "description", "amount", "balance"},
        ),
        (
            ("Date", "Transaction", "Debit", "Credit", "Balance"),
            {"date", "description", "debit", "credit", "balance"},
        ),
    ],
    ids=["layout-A", "layout-B", "layout-C"],
)
def test_detect_columns_recognises_each_layout(
    words: tuple[str, ...], expected: set[str]
) -> None:
    columns = detect_columns(header(*words))

    assert columns is not None
    assert set(columns) == expected


@pytest.mark.parametrize(
    "words",
    [
        ("Date", "Description", "Withdrawals", "Deposits"),  # no balance
        ("Date", "Description", "Debit", "Balance"),  # debit without credit
        ("2026-03-09", "City Transit", "80.00", "-24.20"),  # a data row
        ("Date", "Date", "Description", "Amount", "Balance"),  # duplicate column
    ],
)
def test_detect_columns_returns_none_for_non_headers(words: tuple[str, ...]) -> None:
    assert detect_columns(header(*words)) is None


def test_group_rows_merges_lines_within_tolerance_and_sorts_left_to_right() -> None:
    pieces = [
        TextPiece(x=300, y=177.0, text="80.00"),
        TextPiece(x=40, y=194.0, text="2026-03-10"),
        TextPiece(x=40, y=176.0, text="2026-03-09"),
        TextPiece(x=115, y=177.5, text="City Transit"),
    ]

    rows = group_rows(pieces)

    assert [[p.text for p in row] for row in rows] == [
        ["2026-03-09", "City Transit", "80.00"],
        ["2026-03-10"],
    ]


def test_group_rows_of_nothing_is_empty() -> None:
    assert group_rows([]) == []


@pytest.mark.parametrize(
    ("x", "text", "column"),
    [
        (354.6, "80.00", "debit"),  # small withdrawal, right-aligned
        (338.0, "12,345.67", "debit"),  # wide withdrawal
        (440.0, "10.00", "credit"),  # small deposit
        (527.0, "-1,330.00", "balance"),
    ],
)
def test_assign_cells_uses_nearest_header(x: float, text: str, column: Column) -> None:
    cells = assign_cells([TextPiece(x=x, y=177, text=text)], LAYOUT_A)

    assert cells == {column: text}


def test_assign_cells_strips_and_joins_pieces_in_one_column() -> None:
    row = [
        TextPiece(x=42.8, y=177, text="2026-03-09"),
        TextPiece(x=117.8, y=177, text=" City"),
        TextPiece(x=140.0, y=177, text=" Transit"),
    ]

    cells = assign_cells(row, LAYOUT_A)

    assert cells == {"date": "2026-03-09", "description": "City Transit"}
