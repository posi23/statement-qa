"""Decide what goes on each synthetic statement. Pure data, no PDF code.

Each spec carries `expected`, the `ParsedStatement` the parser should return
for it, so tests can compare parser output against it directly.
"""

import calendar
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

RENT = "Rent - Demo Properties"
PAYROLL = "Payroll ACME Corp"
ELECTRICITY = "Utility Co Electric"
PHONE = "Phone Plan Demo"

# Day of the month each recurring entry lands on. 0 means the last day.
LAST_DAY = 0
RECURRING_DAYS: dict[str, tuple[int, ...]] = {
    RENT: (1,),
    ELECTRICITY: (8,),
    PAYROLL: (15, LAST_DAY),
    PHONE: (20,),
}

_RENT_AMOUNT = Decimal("1450.00")
_CENT = Decimal("0.01")
_MIN_SPEND = Decimal("1.00")

# Everyday entries: (description, lowest amount, highest amount). All made up.
_EVERYDAY_IN = (
    ("Transfer from savings", Decimal("100.00"), Decimal("500.00")),
    ("Refund Online Store", Decimal("10.00"), Decimal("80.00")),
)
_EVERYDAY_OUT = (
    ("Grocery Mart", Decimal("20.00"), Decimal("180.00")),
    ("City Transit", Decimal("3.00"), Decimal("90.00")),
    ("Coffee Corner", Decimal("3.00"), Decimal("12.00")),
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
    # Starts low, so rent on the 1st takes it below zero until payday.
    overdrawn: bool
    misprint: bool


class _Entry(NamedTuple):
    date: dt.date
    # 0 for recurring, 1 for everyday: recurring entries come first on a day,
    # which keeps rent as the very first row on the 1st.
    order: int
    description: str
    amount: Decimal


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


def monthly_dates(start: dt.date, end: dt.date, day: int) -> list[dt.date]:
    """Every date on `day` of the month (or the last day, for `LAST_DAY`) in start..end.

    Works across month and year boundaries, e.g. Dec 15 to Jan 14.
    """
    dates: list[dt.date] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        last = calendar.monthrange(year, month)[1]
        candidate = dt.date(year, month, last if day == LAST_DAY else min(day, last))
        if start <= candidate <= end:
            dates.append(candidate)
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return dates


def _build_spec(blueprint: _Blueprint, rng: random.Random) -> StatementSpec:
    rows_per_page = ROWS_PER_PAGE[blueprint.layout]
    recurring = _recurring_entries(blueprint, rng)
    row_count = rng.randint(
        max(len(recurring), (blueprint.pages - 1) * rows_per_page + 1),
        blueprint.pages * rows_per_page,
    )
    everyday = _fit_to_budget(
        recurring,
        [_everyday_entry(blueprint, rng) for _ in range(row_count - len(recurring))],
        rng,
    )
    # sorted() is stable, so recurring entries keep their schedule order on a day.
    entries = sorted(recurring + everyday, key=lambda e: (e.date, e.order))

    if blueprint.overdrawn:
        opening = _random_amount(rng, Decimal("50.00"), Decimal("300.00"))
    else:
        opening = _random_amount(rng, Decimal("4000.00"), Decimal("7000.00"))

    misprint_index = row_count // 2 if blueprint.misprint else None
    balance = opening
    transactions: list[Transaction] = []
    for index, entry in enumerate(entries):
        balance += entry.amount
        printed = balance + MISPRINT_OFFSET if index == misprint_index else balance
        transactions.append(
            Transaction(
                date=entry.date,
                description=entry.description,
                amount=entry.amount,
                balance=printed,
                page=index // rows_per_page + 1,
            )
        )

    return StatementSpec(
        layout=blueprint.layout,
        bank_name=blueprint.bank_name,
        holder=blueprint.holder,
        expected=ParsedStatement(
            statement_id=blueprint.statement_id,
            account_number=blueprint.account_number,
            period_start=blueprint.period_start,
            period_end=blueprint.period_end,
            opening_balance=opening,
            closing_balance=balance,
            page_count=blueprint.pages,
            transactions=tuple(transactions),
        ),
    )


def _recurring_entries(blueprint: _Blueprint, rng: random.Random) -> list[_Entry]:
    """Rent, bills and pay on their fixed days, with one salary paid each payday."""
    amounts = {
        RENT: -_RENT_AMOUNT,
        ELECTRICITY: -_random_amount(rng, Decimal("60.00"), Decimal("160.00")),
        PAYROLL: _random_amount(rng, Decimal("2400.00"), Decimal("2600.00")),
        PHONE: -_random_amount(rng, Decimal("40.00"), Decimal("90.00")),
    }
    return [
        _Entry(date, 0, description, amounts[description])
        for description, days in RECURRING_DAYS.items()
        for day in days
        for date in monthly_dates(blueprint.period_start, blueprint.period_end, day)
    ]


def _everyday_entry(blueprint: _Blueprint, rng: random.Random) -> _Entry:
    """One random day-to-day entry: about 1 in 10 is money in."""
    span_days = (blueprint.period_end - blueprint.period_start).days
    date = blueprint.period_start + dt.timedelta(days=rng.randint(0, span_days))
    if rng.random() < 0.1:
        description, low, high = rng.choice(_EVERYDAY_IN)
        return _Entry(date, 1, description, _random_amount(rng, low, high))
    description, low, high = rng.choice(_EVERYDAY_OUT)
    return _Entry(date, 1, description, -_random_amount(rng, low, high))


def _fit_to_budget(
    recurring: list[_Entry], everyday: list[_Entry], rng: random.Random
) -> list[_Entry]:
    """Scale everyday spending down so the month roughly balances.

    People spend about what they earn. Without this, a busy three-page month
    spends more than two paychecks and the balance never recovers. Only ever
    scales down, so a coffee never becomes a large purchase.
    """
    income = sum(e.amount for e in recurring + everyday if e.amount > 0)
    bills = -sum(e.amount for e in recurring if e.amount < 0)
    spending = -sum(e.amount for e in everyday if e.amount < 0)
    saving = _random_amount(rng, Decimal("100.00"), Decimal("400.00"))
    budget = income - bills - saving
    # No payday in the period means no budget to fit to; leave spending as drawn.
    if budget <= 0 or spending <= budget:
        return everyday
    factor = budget / spending
    return [
        e._replace(amount=-max((-e.amount * factor).quantize(_CENT), _MIN_SPEND))
        if e.amount < 0
        else e
        for e in everyday
    ]


def _random_amount(rng: random.Random, low: Decimal, high: Decimal) -> Decimal:
    """A whole number of cents between `low` and `high`, with two decimal places."""
    cents = rng.randint(int(low * 100), int(high * 100))
    return (Decimal(cents) / 100).quantize(_CENT)
