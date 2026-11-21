"""Pydantic models for parsed statements.

Money is `Decimal` throughout: float can't represent most cent values exactly,
so sums drift and balance checks fail on correct statements.
"""

import datetime as dt
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Transaction(BaseModel):
    """One row of a statement, exactly as printed."""

    model_config = ConfigDict(frozen=True)

    # `dt.date` because a field named `date` would shadow the type inside the class.
    date: dt.date
    description: str = Field(min_length=1)
    amount: Decimal = Field(description="Signed: negative is money out.")
    balance: Decimal = Field(
        description="Running balance as printed; negative means overdrawn."
    )
    page: int = Field(ge=1, description="1-based page the row appears on.")


class ParsedStatement(BaseModel):
    """Everything the parser reads from one statement PDF."""

    model_config = ConfigDict(frozen=True)

    statement_id: str = Field(min_length=1)
    # With the period, this is what identifies a statement in the real world.
    account_number: str = Field(min_length=1)
    period_start: dt.date
    period_end: dt.date
    opening_balance: Decimal
    closing_balance: Decimal
    page_count: int = Field(ge=1)
    transactions: tuple[Transaction, ...]

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        """Catch impossible statements before anything cites them."""
        if self.period_start > self.period_end:
            raise ValueError(
                f"period starts {self.period_start} after it ends {self.period_end}"
            )
        for transaction in self.transactions:
            # A citation to page 5 of a 3-page PDF would send readers nowhere.
            if transaction.page > self.page_count:
                raise ValueError(
                    f"transaction on page {transaction.page} of a "
                    f"{self.page_count}-page statement"
                )
        return self


class BalanceMismatch(BaseModel):
    """A printed balance that doesn't match opening balance plus amounts so far."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["row", "closing"]
    # None for the closing balance, which isn't a transaction row.
    row_index: int | None
    page: int | None
    expected: Decimal
    printed: Decimal
