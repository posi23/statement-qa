"""Decide what goes on each synthetic statement. Pure data, no PDF code.

Each spec carries `expected`, the `ParsedStatement` the parser should return
for it, so tests can compare parser output against it directly.
"""

import datetime as dt
import random
from decimal import Decimal
from typing import Literal, NamedTuple

from pydantic import BaseModel, ConfigDict

from statement_qa.parsing.models import ParsedStatement, Transaction

Layout = Literal["A", "B", "C"]

DEFAULT_SEED = 42

# Fewer rows per page on some layouts so page breaks fall in different places.
ROWS_PER_PAGE: dict[Layout, int] = {"A": 30, "B": 26, "C": 22}

# Added to one printed balance on the misprinted statement.
MISPRINT_OFFSET = Decimal("100.00")

_RENT = ("Rent - Demo Properties", Decimal("1450.00"))
_PAYDAY = ("Payroll ACME Corp", Decimal("2400.00"), Decimal("2600.00"))
_CENT = Decimal("0.01")

# (description, lowest amount, highest amount). All merchants are made up.
_MONEY_IN = (
    ("Payroll ACME Corp", Decimal("1800.00"), Decimal("2600.00")),
    ("Transfer from savings", Decimal("100.00"), Decimal("500.00")),
    ("Refund Online Store", Decimal("10.00"), Decimal("80.00")),
)
_MONEY_OUT = (
    ("Grocery Mart", Decimal("20.00"), Decimal("180.00")),
    ("City Transit", Decimal("3.00"), Decimal("90.00")),
    ("Coffee Corner", Decimal("3.00"), Decimal("12.00")),
    ("Utility Co Electric", Decimal("60.00"), Decimal("160.00")),
    ("Phone Plan Demo", Decimal("40.00"), Decimal("90.00")),
    ("Online Store", Decimal("15.00"), Decimal("250.00")),
    ("Gas Station", Decimal("30.00"), Decimal("90.00")),
    ("Restaurant Sample", Decimal("20.00"), Decimal("120.00")),
)


class StatementSpec(BaseModel):
    """What to draw for one statement, plus what parsing it should give back."""

    model_config = ConfigDict(frozen=True)

    layout: Layout
    bank_name: str
    holder: str
    account_number: str
    expected: ParsedStatement


class _Blueprint(NamedTuple):
    statement_id: str
    layout: Layout
    bank_name: str
    holder: str
    account_number: str
    period_start: dt.date
    period_end: dt.date
    pages: int
    overdrawn: bool
    misprint: bool


_AURORA = "Aurora Demo Bank"
_CHINOOK = "Chinook Sample Credit Union"
_FOOTHILLS = "Foothills Example Trust"

# Two statements per layout. Columns: id, layout, bank, holder, account,
# period start, period end, pages, overdrawn, misprinted balance.
_BLUEPRINTS = (
    _Blueprint(
        "aurora-demo-2026-03", "A", _AURORA, "Alex Sample", "000-00000-01",
        dt.date(2026, 3, 1), dt.date(2026, 3, 31), 2, True, False,
    ),
    _Blueprint(
        "aurora-demo-2026-04", "A", _AURORA, "Jordan Example", "000-00000-02",
        dt.date(2026, 4, 1), dt.date(2026, 4, 30), 3, False, True,
    ),
    _Blueprint(
        "chinook-sample-2026-06", "B", _CHINOOK, "Sam Placeholder", "000-00000-03",
        dt.date(2026, 6, 1), dt.date(2026, 6, 30), 3, True, False,
    ),
    _Blueprint(
        "chinook-sample-2026-07", "B", _CHINOOK, "Riley Testcase", "000-00000-04",
        dt.date(2026, 7, 1), dt.date(2026, 7, 31), 2, False, False,
    ),
    _Blueprint(
        "foothills-example-2025-12", "C", _FOOTHILLS, "Casey Fictional", "000-00000-05",
        dt.date(2025, 12, 15), dt.date(2026, 1, 14), 4, False, False,
    ),
    _Blueprint(
        "foothills-example-2026-09", "C", _FOOTHILLS, "Morgan Mockup", "000-00000-06",
        dt.date(2026, 9, 1), dt.date(2026, 9, 30), 2, True, False,
    ),
)  # fmt: skip


def build_specs(seed: int = DEFAULT_SEED) -> list[StatementSpec]:
    """Build the synthetic statements. The same seed always gives the same specs."""
    # Not security randomness: a seeded generator makes the data repeatable.
    rng = random.Random(seed)  # noqa: S311
    return [_build_spec(blueprint, rng) for blueprint in _BLUEPRINTS]


def _build_spec(blueprint: _Blueprint, rng: random.Random) -> StatementSpec:
    rows_per_page = ROWS_PER_PAGE[blueprint.layout]
    row_count = rng.randint(
        (blueprint.pages - 1) * rows_per_page + 1, blueprint.pages * rows_per_page
    )
    span_days = (blueprint.period_end - blueprint.period_start).days
    dates = sorted(
        blueprint.period_start + dt.timedelta(days=rng.randint(0, span_days))
        for _ in range(row_count)
    )

    if blueprint.overdrawn:
        opening = _random_amount(rng, Decimal("50.00"), Decimal("300.00"))
    else:
        opening = _random_amount(rng, Decimal("2500.00"), Decimal("6000.00"))

    misprint_index = row_count // 2 if blueprint.misprint else None
    # Overdrawn statements dip below zero after rent and recover on payday.
    payday_index = row_count // 6 if blueprint.overdrawn else None
    balance = opening
    transactions: list[Transaction] = []
    for index, date in enumerate(dates):
        if index == 0 and blueprint.overdrawn:
            # A big payment before any income guarantees the balance goes negative.
            description, amount = _RENT[0], -_RENT[1]
        elif index == payday_index:
            description = _PAYDAY[0]
            amount = _random_amount(rng, _PAYDAY[1], _PAYDAY[2])
        else:
            description, amount = _random_entry(rng)
        balance += amount
        printed = balance + MISPRINT_OFFSET if index == misprint_index else balance
        transactions.append(
            Transaction(
                date=date,
                description=description,
                amount=amount,
                balance=printed,
                page=index // rows_per_page + 1,
            )
        )

    return StatementSpec(
        layout=blueprint.layout,
        bank_name=blueprint.bank_name,
        holder=blueprint.holder,
        account_number=blueprint.account_number,
        expected=ParsedStatement(
            statement_id=blueprint.statement_id,
            period_start=blueprint.period_start,
            period_end=blueprint.period_end,
            opening_balance=opening,
            closing_balance=balance,
            page_count=blueprint.pages,
            transactions=tuple(transactions),
        ),
    )


def _random_entry(rng: random.Random) -> tuple[str, Decimal]:
    """One made-up transaction: about 1 in 5 is money in."""
    if rng.random() < 0.2:
        description, low, high = rng.choice(_MONEY_IN)
        return description, _random_amount(rng, low, high)
    description, low, high = rng.choice(_MONEY_OUT)
    return description, -_random_amount(rng, low, high)


def _random_amount(rng: random.Random, low: Decimal, high: Decimal) -> Decimal:
    """A whole number of cents between `low` and `high`, with two decimal places."""
    cents = rng.randint(int(low * 100), int(high * 100))
    return (Decimal(cents) / 100).quantize(_CENT)
