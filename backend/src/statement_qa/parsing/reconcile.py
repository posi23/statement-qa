"""Check whether a statement's printed balances add up."""

from statement_qa.parsing.models import BalanceMismatch, ParsedStatement


def find_balance_mismatches(statement: ParsedStatement) -> list[BalanceMismatch]:
    """Return every printed balance that isn't opening balance plus amounts so far.

    The expected balance is carried forward from the amounts, not from the
    previous printed balance, so a single misprinted row is reported once
    instead of also flagging the row after it.
    """
    mismatches: list[BalanceMismatch] = []
    expected = statement.opening_balance
    for index, transaction in enumerate(statement.transactions):
        expected += transaction.amount
        if transaction.balance != expected:
            mismatches.append(
                BalanceMismatch(
                    kind="row",
                    row_index=index,
                    page=transaction.page,
                    expected=expected,
                    printed=transaction.balance,
                )
            )
    if statement.closing_balance != expected:
        mismatches.append(
            BalanceMismatch(
                kind="closing",
                row_index=None,
                page=None,
                expected=expected,
                printed=statement.closing_balance,
            )
        )
    return mismatches
