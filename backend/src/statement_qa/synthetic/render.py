"""Draw a `StatementSpec` as a PDF with fpdf2."""

import datetime as dt
from collections.abc import Callable
from decimal import Decimal
from typing import Literal, NamedTuple

from fpdf import FPDF

from statement_qa.parsing.models import Transaction
from statement_qa.synthetic.spec import Layout, StatementSpec

BANNER = "SYNTHETIC SAMPLE - NOT A REAL STATEMENT"

# A fixed creation date keeps the bytes identical between runs, so
# regenerating the committed PDFs doesn't show up as a git diff.
_CREATED = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)

_FONT_SIZE = 9
_LEFT = 40.0
_RIGHT = 572.0
_LABEL_VALUE_X = 160.0
_TABLE_HEADER_Y = 160.0
_ROW_HEIGHT = 17.0


class _Cell(NamedTuple):
    header: str
    x: float
    width: float
    align: Literal["L", "R"]


def _money(value: Decimal) -> str:
    return f"{abs(value):,.2f}"


def _signed(value: Decimal) -> str:
    return f"-{_money(value)}" if value < 0 else _money(value)


def _overdrawn_suffix(value: Decimal) -> str:
    return f"{_money(value)} OD" if value < 0 else _money(value)


def _dollar_parens(value: Decimal) -> str:
    return f"(${_money(value)})" if value < 0 else f"${_money(value)}"


class _Style(NamedTuple):
    """How one layout prints its table and values."""

    cells: tuple[_Cell, ...]
    row_date: str
    period_date: str
    balance: Callable[[Decimal], str]
    # Money columns: "signed" is one Amount column, "split" is Debit + Credit.
    money: Literal["signed", "split"]
    dollar_sign: bool


_STYLES: dict[Layout, _Style] = {
    "A": _Style(
        cells=(
            _Cell("Date", 40, 70, "L"),
            _Cell("Description", 115, 180, "L"),
            _Cell("Withdrawals", 300, 80, "R"),
            _Cell("Deposits", 385, 80, "R"),
            _Cell("Balance", 470, 100, "R"),
        ),
        row_date="%Y-%m-%d",
        period_date="%Y-%m-%d",
        balance=_signed,
        money="split",
        dollar_sign=False,
    ),
    "B": _Style(
        cells=(
            _Cell("Date", 40, 75, "L"),
            _Cell("Details", 120, 200, "L"),
            _Cell("Amount", 330, 100, "R"),
            _Cell("Balance", 440, 130, "R"),
        ),
        row_date="%d %b %Y",
        period_date="%d %b %Y",
        balance=_overdrawn_suffix,
        money="signed",
        dollar_sign=False,
    ),
    "C": _Style(
        cells=(
            _Cell("Date", 40, 50, "L"),
            _Cell("Transaction", 95, 190, "L"),
            _Cell("Debit", 290, 85, "R"),
            _Cell("Credit", 380, 85, "R"),
            _Cell("Balance", 470, 100, "R"),
        ),
        row_date="%b %d",
        period_date="%b %d, %Y",
        balance=_dollar_parens,
        money="split",
        dollar_sign=True,
    ),
}


def _row_values(transaction: Transaction, style: _Style) -> tuple[str, ...]:
    """The strings printed in each cell of one row, in column order."""
    date = transaction.date.strftime(style.row_date)
    balance = style.balance(transaction.balance)
    if style.money == "signed":
        return (date, transaction.description, _signed(transaction.amount), balance)
    amount = _money(transaction.amount)
    if style.dollar_sign:
        amount = f"${amount}"
    debit, credit = (amount, "") if transaction.amount < 0 else ("", amount)
    return (date, transaction.description, debit, credit, balance)


def render_pdf(spec: StatementSpec) -> bytes:
    """Draw the statement and return the PDF bytes."""
    style = _STYLES[spec.layout]
    expected = spec.expected
    pdf = FPDF(unit="pt", format="letter")
    pdf.set_auto_page_break(auto=False)
    pdf.set_creation_date(_CREATED)
    pdf.set_title(f"{spec.bank_name} statement {expected.statement_id} (synthetic)")
    pdf.set_author("statement-qa synthetic generator")

    for page in range(1, expected.page_count + 1):
        pdf.add_page()
        _draw_page_header(pdf, spec.bank_name, page, expected.page_count)
        if page == 1:
            period = (
                f"{expected.period_start.strftime(style.period_date)} to "
                f"{expected.period_end.strftime(style.period_date)}"
            )
            _draw_summary(
                pdf,
                (
                    ("Account holder:", spec.holder),
                    ("Account:", spec.account_number),
                    ("Statement period:", period),
                    ("Opening balance:", style.balance(expected.opening_balance)),
                    ("Closing balance:", style.balance(expected.closing_balance)),
                ),
            )
        rows = [t for t in expected.transactions if t.page == page]
        _draw_table(pdf, style, rows)

    return bytes(pdf.output())


def _text(
    pdf: FPDF,
    x: float,
    y: float,
    text: str,
    width: float = 0,
    align: Literal["L", "R"] = "L",
) -> None:
    pdf.set_xy(x, y)
    pdf.cell(w=width, text=text, align=align)


def _draw_page_header(pdf: FPDF, bank_name: str, page: int, page_count: int) -> None:
    pdf.set_font("Helvetica", style="B", size=_FONT_SIZE)
    _text(pdf, _LEFT, 30, BANNER)
    pdf.set_font("Helvetica", size=_FONT_SIZE + 3)
    _text(pdf, _LEFT, 50, bank_name)
    pdf.set_font("Helvetica", size=_FONT_SIZE)
    _text(
        pdf, _LEFT, 50, f"Page {page} of {page_count}", width=_RIGHT - _LEFT, align="R"
    )


def _draw_summary(pdf: FPDF, lines: tuple[tuple[str, str], ...]) -> None:
    pdf.set_font("Helvetica", size=_FONT_SIZE)
    for index, (label, value) in enumerate(lines):
        y = 70 + index * 15
        _text(pdf, _LEFT, y, label)
        _text(pdf, _LABEL_VALUE_X, y, value)


def _draw_table(pdf: FPDF, style: _Style, rows: list[Transaction]) -> None:
    pdf.set_font("Helvetica", style="B", size=_FONT_SIZE)
    for cell in style.cells:
        _text(pdf, cell.x, _TABLE_HEADER_Y, cell.header, cell.width, cell.align)
    pdf.line(_LEFT, _TABLE_HEADER_Y + 12, _RIGHT, _TABLE_HEADER_Y + 12)

    pdf.set_font("Helvetica", size=_FONT_SIZE)
    for index, transaction in enumerate(rows):
        y = _TABLE_HEADER_Y + (index + 1) * _ROW_HEIGHT
        for cell, value in zip(
            style.cells, _row_values(transaction, style), strict=True
        ):
            if value:
                _text(pdf, cell.x, y, value, cell.width, cell.align)
