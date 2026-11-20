"""Tests for the consistency checks on `ParsedStatement`."""

import datetime as dt
from decimal import Decimal

import pytest
from pydantic import ValidationError

from statement_qa.parsing.models import ParsedStatement, Transaction


def _statement(
    period_start: dt.date = dt.date(2026, 3, 1),
    period_end: dt.date = dt.date(2026, 3, 31),
    page_count: int = 2,
    transaction_page: int = 2,
) -> ParsedStatement:
    return ParsedStatement(
        statement_id="test-statement",
        period_start=period_start,
        period_end=period_end,
        opening_balance=Decimal("100.00"),
        closing_balance=Decimal("90.00"),
        page_count=page_count,
        transactions=(
            Transaction(
                date=dt.date(2026, 3, 2),
                description="Coffee Corner",
                amount=Decimal("-10.00"),
                balance=Decimal("90.00"),
                page=transaction_page,
            ),
        ),
    )


def test_consistent_statement_is_accepted() -> None:
    assert _statement().page_count == 2


def test_one_day_period_is_accepted() -> None:
    day = dt.date(2026, 3, 2)

    assert _statement(period_start=day, period_end=day).period_start == day


def test_period_that_ends_before_it_starts_is_rejected() -> None:
    with pytest.raises(ValidationError, match="after it ends"):
        _statement(period_start=dt.date(2026, 3, 31), period_end=dt.date(2026, 3, 1))


def test_transaction_on_a_page_past_the_end_is_rejected() -> None:
    with pytest.raises(ValidationError, match="page 3 of a 2-page"):
        _statement(page_count=2, transaction_page=3)
