"""Tests for parsing statement PDFs, with the synthetic specs as the answer key."""

import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest
from fpdf import FPDF

from statement_qa.parsing import (
    StatementParseError,
    find_balance_mismatches,
    parse_statement,
    parse_statement_file,
)
from statement_qa.synthetic import StatementSpec, build_specs, render_pdf
from statement_qa.synthetic.spec import MISPRINT_OFFSET

SPECS = build_specs()
SPECS_BY_ID = {spec.expected.statement_id: spec for spec in SPECS}
# tests/parsing/test_parser.py -> repo root
DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "synthetic"


def _id(spec: StatementSpec) -> str:
    return spec.expected.statement_id


@pytest.mark.parametrize("spec", SPECS, ids=_id)
def test_parser_reads_every_generated_statement_exactly(spec: StatementSpec) -> None:
    parsed = parse_statement(render_pdf(spec), spec.expected.statement_id)

    assert parsed == spec.expected


def test_year_crossing_statement_dates_land_in_both_years() -> None:
    spec = SPECS_BY_ID["foothills-example-2025-12"]

    parsed = parse_statement(render_pdf(spec), "foothills-example-2025-12")

    assert parsed.period_start == dt.date(2025, 12, 15)
    assert parsed.period_end == dt.date(2026, 1, 14)
    assert {t.date.year for t in parsed.transactions} == {2025, 2026}


@pytest.mark.parametrize(
    "statement_id",
    ["aurora-demo-2026-03", "chinook-sample-2026-06", "foothills-example-2026-09"],
    ids=["layout-A", "layout-B", "layout-C"],
)
def test_overdrawn_balances_parse_as_negative(statement_id: str) -> None:
    parsed = parse_statement(render_pdf(SPECS_BY_ID[statement_id]), statement_id)

    assert any(t.balance < 0 for t in parsed.transactions)


def test_misprinted_balance_is_kept_and_flagged() -> None:
    misprinted = [s for s in SPECS if find_balance_mismatches(s.expected)]
    assert len(misprinted) == 1
    spec = misprinted[0]

    parsed = parse_statement(render_pdf(spec), spec.expected.statement_id)
    mismatches = find_balance_mismatches(parsed)

    assert len(mismatches) == 1
    mismatch = mismatches[0]
    assert mismatch.kind == "row"
    assert mismatch.printed - mismatch.expected == MISPRINT_OFFSET


def test_committed_statements_match_the_generator() -> None:
    paths = sorted(DATA_DIR.glob("*.pdf"))

    assert {p.stem for p in paths} == set(SPECS_BY_ID)
    for path in paths:
        assert parse_statement_file(path) == SPECS_BY_ID[path.stem].expected


def test_non_pdf_bytes_raise() -> None:
    with pytest.raises(StatementParseError, match="not a readable PDF"):
        parse_statement(b"this is not a pdf", "junk")


Row = tuple[str, ...]


def _pdf(*pages: list[Row], spacing: float = 120) -> bytes:
    """Hand-built PDF for edge cases: one list of rows per page.

    Each row's strings are left-aligned `spacing` points apart, so a value
    starts exactly under its header. Empty strings leave a cell blank.
    """
    pdf = FPDF(unit="pt", format="letter")
    pdf.set_font("Helvetica", size=9)
    for rows in pages:
        pdf.add_page()
        for row_index, row in enumerate(rows):
            for column_index, text in enumerate(row):
                if text:
                    pdf.set_xy(40 + column_index * spacing, 40 + row_index * 15)
                    pdf.cell(text=text)
    return bytes(pdf.output())


SUMMARY: list[Row] = [
    ("Statement period:", "2026-03-01 to 2026-03-31"),
    ("Opening balance:", "100.00"),
    ("Closing balance:", "36.00"),
]
HEADER: Row = ("Date", "Description", "Withdrawals", "Deposits", "Balance")


def _one_page(*rows: Row) -> bytes:
    return _pdf([*SUMMARY, HEADER, *rows])


def test_pdf_without_a_transaction_table_raises() -> None:
    pdf = _pdf([*SUMMARY, ("Thank you for banking with us.",)])

    with pytest.raises(StatementParseError, match="no transaction table"):
        parse_statement(pdf, "no-table")


def test_pdf_without_a_summary_raises() -> None:
    pdf = _pdf([("Just a letter, not a statement.",)])

    with pytest.raises(StatementParseError, match="summary is missing"):
        parse_statement(pdf, "no-summary")


def test_page_without_a_header_reuses_the_previous_columns() -> None:
    pdf = _pdf(
        [*SUMMARY, HEADER, ("2026-03-02", "Coffee Corner", "4.00", "", "96.00")],
        [("Page 2 of 2",), ("2026-03-20", "Grocery Mart", "60.00", "", "36.00")],
    )

    parsed = parse_statement(pdf, "headerless-page-2")

    assert [(t.description, t.page) for t in parsed.transactions] == [
        ("Coffee Corner", 1),
        ("Grocery Mart", 2),
    ]


def test_balance_lines_and_footers_are_skipped() -> None:
    pdf = _one_page(
        ("", "Balance brought forward", "", "", "100.00"),
        ("2026-03-02", "Coffee Corner", "4.00", "", "96.00"),
        ("", "Closing balance", "", "", "96.00"),
        ("Continued overleaf",),
    )

    parsed = parse_statement(pdf, "balance-lines")

    assert [t.description for t in parsed.transactions] == ["Coffee Corner"]


def test_row_with_money_and_an_unreadable_date_raises() -> None:
    # Letter O instead of zero: before, this row vanished without an error.
    pdf = _one_page(("2026-O3-09", "City Transit", "80.00", "", "20.00"))

    with pytest.raises(StatementParseError, match="unreadable date"):
        parse_statement(pdf, "garbled-date")


@pytest.mark.parametrize(
    ("withdrawal", "deposit"), [("4.00", "5.00"), ("", "")], ids=["both", "neither"]
)
def test_row_needs_exactly_one_of_debit_or_credit(
    withdrawal: str, deposit: str
) -> None:
    pdf = _one_page(("2026-03-02", "Coffee Corner", withdrawal, deposit, "96.00"))

    with pytest.raises(StatementParseError, match="exactly one of debit or credit"):
        parse_statement(pdf, "bad-money")


def test_row_without_a_description_raises() -> None:
    pdf = _one_page(("2026-03-02", "", "4.00", "", "96.00"))

    with pytest.raises(StatementParseError, match="page 1, row dated 2026-03-02"):
        parse_statement(pdf, "no-description")


def test_summary_label_and_value_in_one_string() -> None:
    pdf = _pdf(
        [
            ("Statement period: 2026-03-01 to 2026-03-31",),
            ("Opening balance: 100.00",),
            ("Closing balance: 96.00",),
            HEADER,
            ("2026-03-02", "Coffee Corner", "4.00", "", "96.00"),
        ]
    )

    parsed = parse_statement(pdf, "one-string-summary")

    assert (parsed.period_start, parsed.opening_balance) == (
        dt.date(2026, 3, 1),
        Decimal("100.00"),
    )


def test_unit_suffixes_synonyms_and_unused_columns() -> None:
    pdf = _pdf(
        [
            *SUMMARY,
            ("Date", "Ref", "Particulars", "Money out ($)", "Money in ($)", "Balance"),
            ("2026-03-02", "A1B2", "Coffee Corner", "4.00", "", "96.00"),
        ],
        spacing=95,
    )

    parsed = parse_statement(pdf, "other-headers")

    assert parsed.transactions[0].description == "Coffee Corner"
    assert parsed.transactions[0].amount == Decimal("-4.00")


def test_inconsistent_statement_raises_a_parse_error() -> None:
    pdf = _pdf(
        [
            ("Statement period:", "2026-03-31 to 2026-03-01"),
            ("Opening balance:", "100.00"),
            ("Closing balance:", "96.00"),
            HEADER,
            ("2026-03-02", "Coffee Corner", "4.00", "", "96.00"),
        ]
    )

    with pytest.raises(StatementParseError, match="inconsistent statement"):
        parse_statement(pdf, "backwards-period")
