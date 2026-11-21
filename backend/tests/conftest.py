"""Shared test helpers. All data is made up."""

import datetime as dt
from collections.abc import Callable
from decimal import Decimal

import pytest

from statement_qa.parsing.models import ParsedStatement, Transaction

TransactionFactory = Callable[..., Transaction]
StatementFactory = Callable[..., ParsedStatement]


@pytest.fixture
def make_transaction() -> TransactionFactory:
    """Build a `Transaction`, overriding only the fields a test cares about."""

    def factory(
        amount: str = "-10.00",
        balance: str = "90.00",
        date: dt.date = dt.date(2026, 3, 2),
        description: str = "Coffee Corner",
        page: int = 1,
    ) -> Transaction:
        return Transaction(
            date=date,
            description=description,
            amount=Decimal(amount),
            balance=Decimal(balance),
            page=page,
        )

    return factory


@pytest.fixture
def make_statement() -> StatementFactory:
    """Build a `ParsedStatement` around a list of transactions."""

    def factory(
        transactions: list[Transaction],
        opening: str = "100.00",
        closing: str | None = None,
    ) -> ParsedStatement:
        last = transactions[-1].balance if transactions else Decimal(opening)
        return ParsedStatement(
            statement_id="test-statement",
            account_number="000-00000-99",
            period_start=dt.date(2026, 3, 1),
            period_end=dt.date(2026, 3, 31),
            opening_balance=Decimal(opening),
            closing_balance=Decimal(closing) if closing is not None else last,
            page_count=max((t.page for t in transactions), default=1),
            transactions=tuple(transactions),
        )

    return factory
