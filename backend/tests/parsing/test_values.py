"""Tests for parsing printed amounts and dates."""

import datetime as dt
from decimal import Decimal

import pytest

from statement_qa.parsing.values import parse_amount, parse_full_date, parse_row_date

MARCH = (dt.date(2026, 3, 1), dt.date(2026, 3, 31))
NEW_YEAR = (dt.date(2025, 12, 15), dt.date(2026, 1, 14))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.34", "12.34"),
        ("1,234.56", "1234.56"),
        ("$1,234.56", "1234.56"),
        ("-45.20", "-45.20"),
        ("(45.20)", "-45.20"),
        ("($45.20)", "-45.20"),
        ("45.20 OD", "-45.20"),
        ("0.00", "0.00"),
        (" 80.00 ", "80.00"),
    ],
)
def test_parse_amount_reads_printed_formats(text: str, expected: str) -> None:
    assert parse_amount(text) == Decimal(expected)


@pytest.mark.parametrize("text", ["", "abc", "12.3", "1.234", "--5.00", "OD"])
def test_parse_amount_rejects_non_amounts(text: str) -> None:
    with pytest.raises(ValueError, match="not an amount"):
        parse_amount(text)


@pytest.mark.parametrize(
    "text", ["2026-03-04", "04 Mar 2026", "Mar 04, 2026", " 2026-03-04 "]
)
def test_parse_full_date_reads_each_format(text: str) -> None:
    assert parse_full_date(text) == dt.date(2026, 3, 4)


def test_parse_row_date_takes_year_from_period() -> None:
    assert parse_row_date("Mar 04", *MARCH) == dt.date(2026, 3, 4)


@pytest.mark.parametrize(
    ("text", "expected"),
    [("Dec 20", dt.date(2025, 12, 20)), ("Jan 03", dt.date(2026, 1, 3))],
)
def test_parse_row_date_picks_the_year_across_new_year(
    text: str, expected: dt.date
) -> None:
    assert parse_row_date(text, *NEW_YEAR) == expected


@pytest.mark.parametrize("text", ["Feb 03", "Payroll", "", "2026-13-01"])
def test_parse_row_date_rejects_bad_or_out_of_period_dates(text: str) -> None:
    with pytest.raises(ValueError, match="not a date"):
        parse_row_date(text, *MARCH)
