"""Parse a statement PDF into a `ParsedStatement`.

Values are kept exactly as printed. A wrong printed balance stays wrong here;
`find_balance_mismatches` is where that gets judged.
"""

import datetime as dt
from decimal import Decimal
from pathlib import Path

from statement_qa.parsing.errors import StatementParseError
from statement_qa.parsing.layout import (
    Column,
    TextPiece,
    assign_cells,
    detect_columns,
    group_rows,
)
from statement_qa.parsing.models import ParsedStatement, Transaction
from statement_qa.parsing.reader import read_pages
from statement_qa.parsing.values import parse_amount, parse_full_date, parse_row_date


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

    summary = _read_summary(pages[0])
    period_start, period_end = _parse_period(summary["statement period"])
    found_table = False
    transactions: list[Transaction] = []
    for page_number, rows in enumerate(pages, start=1):
        table = _find_table(rows)
        if table is None:
            continue
        found_table = True
        columns, body = table
        for row in body:
            transaction = _parse_row(
                row, columns, page_number, period_start, period_end
            )
            if transaction is not None:
                transactions.append(transaction)
    if not found_table:
        raise StatementParseError("no transaction table found")

    return ParsedStatement(
        statement_id=statement_id,
        period_start=period_start,
        period_end=period_end,
        opening_balance=_amount(summary["opening balance"], "opening balance"),
        closing_balance=_amount(summary["closing balance"], "closing balance"),
        page_count=len(pages),
        transactions=tuple(transactions),
    )


_SUMMARY_LABELS = ("statement period", "opening balance", "closing balance")


def _read_summary(rows: list[list[TextPiece]]) -> dict[str, str]:
    """Find `Label: value` rows on the first page."""
    summary: dict[str, str] = {}
    for row in rows:
        label = row[0].text.strip().rstrip(":").lower()
        if label in _SUMMARY_LABELS and len(row) > 1:
            summary[label] = " ".join(piece.text.strip() for piece in row[1:])
    missing = [label for label in _SUMMARY_LABELS if label not in summary]
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


def _find_table(
    rows: list[list[TextPiece]],
) -> tuple[dict[Column, float], list[list[TextPiece]]] | None:
    """Return the header's columns and the rows below it, or None if no table."""
    for index, row in enumerate(rows):
        columns = detect_columns(row)
        if columns is not None:
            return columns, rows[index + 1 :]
    return None


def _parse_row(
    row: list[TextPiece],
    columns: dict[Column, float],
    page: int,
    period_start: dt.date,
    period_end: dt.date,
) -> Transaction | None:
    """Parse one table row, or return None if its date column holds no date."""
    cells = assign_cells(row, columns)
    try:
        date = parse_row_date(cells.get("date", ""), period_start, period_end)
    except ValueError:
        return None
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
