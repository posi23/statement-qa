"""Parse a statement PDF into a `ParsedStatement`.

Values are kept exactly as printed. A wrong printed balance stays wrong here;
`find_balance_mismatches` is where that gets judged.
"""

import datetime as dt
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from statement_qa.parsing.errors import StatementParseError
from statement_qa.parsing.layout import (
    Column,
    HeaderColumn,
    TextPiece,
    assign_cells,
    detect_columns,
    group_rows,
    normalise_label,
)
from statement_qa.parsing.models import ParsedStatement, Transaction
from statement_qa.parsing.reader import read_pages
from statement_qa.parsing.values import parse_amount, parse_full_date, parse_row_date

# Printed summary label (in `normalise_label` form) -> the field it fills.
_SUMMARY_LABELS: dict[str, str] = {
    "account": "account",
    "account number": "account",
    "account no": "account",
    "statement period": "statement period",
    "opening balance": "opening balance",
    "closing balance": "closing balance",
}
_REQUIRED_SUMMARY = (
    "account",
    "statement period",
    "opening balance",
    "closing balance",
)

# Lines inside the table that carry money but aren't transactions.
_BALANCE_LINES = frozenset(
    {
        "opening balance",
        "closing balance",
        "balance brought forward",
        "balance carried forward",
        "brought forward",
        "carried forward",
        "total",
        "totals",
    }
)

_MONEY_COLUMNS: tuple[Column, ...] = ("amount", "debit", "credit", "balance")


def parse_statement_file(path: Path) -> ParsedStatement:
    """Parse a statement file; its file name without `.pdf` is the statement id."""
    return parse_statement(path.read_bytes(), statement_id=path.stem)


def parse_statement(pdf: bytes, statement_id: str) -> ParsedStatement:
    """Parse statement PDF bytes.

    Raises:
        StatementParseError: if the bytes aren't a PDF, the summary or the
            transaction table is missing, or a transaction row doesn't parse.
    """
    pages = [group_rows(pieces) for pieces in read_pages(pdf)]
    if not pages:
        raise StatementParseError("PDF has no pages")

    # Only rows above the table count as summary, so a `Closing balance` line
    # inside the table can't overwrite the printed summary value.
    first_header = _find_header(pages[0])
    summary_rows = pages[0] if first_header is None else pages[0][: first_header[0]]
    summary = _read_summary(summary_rows)
    period_start, period_end = _parse_period(summary["statement period"])
    columns: list[HeaderColumn] | None = None
    transactions: list[Transaction] = []
    for page_number, rows in enumerate(pages, start=1):
        header = _find_header(rows)
        if header is not None:
            header_index, columns = header
            body = rows[header_index + 1 :]
        elif columns is not None:
            # Many statements print the header on the first page only.
            body = rows
        else:
            continue
        for row in body:
            transaction = _parse_row(
                row, columns, page_number, period_start, period_end
            )
            if transaction is not None:
                transactions.append(transaction)
    if columns is None:
        raise StatementParseError("no transaction table found")

    try:
        return ParsedStatement(
            statement_id=statement_id,
            account_number=summary["account"],
            period_start=period_start,
            period_end=period_end,
            opening_balance=_amount(summary["opening balance"], "opening balance"),
            closing_balance=_amount(summary["closing balance"], "closing balance"),
            page_count=len(pages),
            transactions=tuple(transactions),
        )
    except ValidationError as error:
        raise StatementParseError(f"inconsistent statement: {error}") from error


def _read_summary(rows: list[list[TextPiece]]) -> dict[str, str]:
    """Find `Label: value` rows in the summary above the first page's table.

    The label and value may be separate strings or one string split at `:`.
    """
    summary: dict[str, str] = {}
    for row in rows:
        label, _, rest = row[0].text.partition(":")
        parts = [rest, *(piece.text for piece in row[1:])]
        value = " ".join(part.strip() for part in parts if part.strip())
        field = _SUMMARY_LABELS.get(normalise_label(label))
        if field is not None and value:
            summary[field] = value
    missing = [field for field in _REQUIRED_SUMMARY if field not in summary]
    if missing:
        raise StatementParseError(f"summary is missing: {', '.join(missing)}")
    return summary


def _parse_period(text: str) -> tuple[dt.date, dt.date]:
    """Parse `<start> to <end>`."""
    start_text, separator, end_text = text.partition(" to ")
    try:
        if not separator:
            raise ValueError("expected '<start> to <end>'")
        return parse_full_date(start_text), parse_full_date(end_text)
    except ValueError as error:
        raise StatementParseError(f"bad statement period {text!r}: {error}") from error


def _amount(text: str, what: str) -> Decimal:
    try:
        return parse_amount(text)
    except ValueError as error:
        raise StatementParseError(f"bad {what}: {error}") from error


def _find_header(
    rows: list[list[TextPiece]],
) -> tuple[int, list[HeaderColumn]] | None:
    """Return the first header row's index and its columns, or None if no header."""
    for index, row in enumerate(rows):
        columns = detect_columns(row)
        if columns is not None:
            return index, columns
    return None


def _parse_row(
    row: list[TextPiece],
    columns: list[HeaderColumn],
    page: int,
    period_start: dt.date,
    period_end: dt.date,
) -> Transaction | None:
    """Parse one table row, or return None if it isn't a transaction.

    Rows without a date are skipped only when they're clearly not transactions:
    no money in them (a footer), or a balance line like `Closing balance`. A
    row with money and an unreadable date raises, so a transaction is never
    dropped silently.
    """
    cells = assign_cells(row, columns)
    if _is_balance_line(cells):
        return None
    try:
        date = parse_row_date(cells.get("date", ""), period_start, period_end)
    except ValueError as error:
        if not _has_money(cells):
            return None
        raise StatementParseError(
            f"page {page}: row with amounts has an unreadable date: "
            f"{cells.get('date', '')!r}"
        ) from error
    try:
        return Transaction(
            date=date,
            description=cells.get("description", ""),
            amount=_row_amount(cells),
            balance=parse_amount(cells.get("balance", "")),
            page=page,
        )
    except ValueError as error:
        # Pydantic's ValidationError is a ValueError too, e.g. an empty description.
        raise StatementParseError(f"page {page}, row dated {date}: {error}") from error


def _is_balance_line(cells: dict[Column, str]) -> bool:
    """True for lines like `Balance brought forward 80.60` that aren't transactions."""
    return any(
        normalise_label(cells.get(column, "")) in _BALANCE_LINES
        for column in ("date", "description")
    )


def _has_money(cells: dict[Column, str]) -> bool:
    """True if any money column holds a readable amount."""
    for column in _MONEY_COLUMNS:
        try:
            parse_amount(cells.get(column, ""))
        except ValueError:
            continue
        return True
    return False


def _row_amount(cells: dict[Column, str]) -> Decimal:
    """Signed amount from either a signed `amount` cell or one of `debit` / `credit`."""
    if "amount" in cells:
        return parse_amount(cells["amount"])
    debit, credit = cells.get("debit"), cells.get("credit")
    if debit is not None and credit is None:
        return -abs(parse_amount(debit))
    if credit is not None and debit is None:
        return abs(parse_amount(credit))
    raise ValueError("expected exactly one of debit or credit")
