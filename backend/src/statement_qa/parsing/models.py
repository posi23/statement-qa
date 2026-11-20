"""Pydantic models for parsed statements.

Money is `Decimal` throughout: float can't represent most cent values exactly,
so sums drift and balance checks fail on correct statements.
"""

import datetime as dt
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
    period_start: dt.date
    period_end: dt.date
    opening_balance: Decimal
    closing_balance: Decimal
    page_count: int = Field(ge=1)
    transactions: tuple[Transaction, ...]


class BalanceMismatch(BaseModel):
    """A printed balance that doesn't match opening balance plus amounts so far."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["row", "closing"]
    # None for the closing balance, which isn't a transaction row.
    row_index: int | None
    page: int | None
    expected: Decimal
    printed: Decimal
