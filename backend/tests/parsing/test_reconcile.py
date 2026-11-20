"""Tests for the balance check."""

from collections.abc import Callable
from decimal import Decimal

from statement_qa.parsing.models import BalanceMismatch, ParsedStatement, Transaction
from statement_qa.parsing.reconcile import find_balance_mismatches

# Types of the `make_transaction` and `make_statement` fixtures in conftest.py.
TransactionFactory = Callable[..., Transaction]
StatementFactory = Callable[..., ParsedStatement]


def test_clean_statement_has_no_mismatches(
    make_transaction: TransactionFactory, make_statement: StatementFactory
) -> None:
    statement = make_statement(
        [
            make_transaction(amount="-30.00", balance="70.00"),
            make_transaction(amount="-100.00", balance="-30.00"),  # overdrawn is fine
            make_transaction(amount="50.00", balance="20.00"),
        ]
    )

    assert find_balance_mismatches(statement) == []


def test_one_misprinted_row_is_reported_once(
    make_transaction: TransactionFactory, make_statement: StatementFactory
) -> None:
    statement = make_statement(
        [
            make_transaction(amount="50.00", balance="150.00"),
            # Printed 230.00, but 150.00 - 20.00 is 130.00.
            make_transaction(amount="-20.00", balance="230.00", page=2),
            # Carries on from the true 130.00, so it isn't flagged too.
            make_transaction(amount="-30.00", balance="100.00"),
        ]
    )

    assert find_balance_mismatches(statement) == [
        BalanceMismatch(
            kind="row",
            row_index=1,
            page=2,
            expected=Decimal("130.00"),
            printed=Decimal("230.00"),
        )
    ]


def test_wrong_closing_balance_is_reported(
    make_transaction: TransactionFactory, make_statement: StatementFactory
) -> None:
    statement = make_statement(
        [make_transaction(amount="-10.00", balance="90.00")], closing="95.00"
    )

    assert find_balance_mismatches(statement) == [
        BalanceMismatch(
            kind="closing",
            row_index=None,
            page=None,
            expected=Decimal("90.00"),
            printed=Decimal("95.00"),
        )
    ]


def test_empty_statement_reconciles_when_closing_equals_opening(
    make_statement: StatementFactory,
) -> None:
    assert find_balance_mismatches(make_statement([], opening="100.00")) == []


def test_empty_statement_with_different_closing_is_reported(
    make_statement: StatementFactory,
) -> None:
    mismatches = find_balance_mismatches(
        make_statement([], opening="100.00", closing="0.00")
    )

    assert [m.kind for m in mismatches] == ["closing"]
