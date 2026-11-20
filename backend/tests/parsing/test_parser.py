"""Tests for parsing statement PDFs, with the synthetic specs as the answer key."""

import datetime as dt
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


def _pdf_with_rows(*rows: tuple[str, ...]) -> bytes:
    """A one-page PDF; each row's strings are drawn 120pt apart, like label/value."""
    pdf = FPDF(unit="pt", format="letter")
    pdf.set_font("Helvetica", size=9)
    pdf.add_page()
    for row_index, row in enumerate(rows):
        for column_index, text in enumerate(row):
            pdf.set_xy(40 + column_index * 120, 40 + row_index * 15)
            pdf.cell(text=text)
    return bytes(pdf.output())


def test_pdf_without_a_transaction_table_raises() -> None:
    pdf = _pdf_with_rows(
        ("Statement period:", "2026-03-01 to 2026-03-31"),
        ("Opening balance:", "10.00"),
        ("Closing balance:", "10.00"),
        ("Thank you for banking with us.",),
    )

    with pytest.raises(StatementParseError, match="no transaction table"):
        parse_statement(pdf, "no-table")


def test_pdf_without_a_summary_raises() -> None:
    pdf = _pdf_with_rows(("Just a letter, not a statement.",))

    with pytest.raises(StatementParseError, match="summary is missing"):
        parse_statement(pdf, "no-summary")
