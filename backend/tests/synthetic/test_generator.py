"""Tests for the synthetic statement generator."""

import datetime as dt
import io
from collections import Counter
from pathlib import Path

import pytest
from pypdf import PdfReader

from statement_qa.parsing import find_balance_mismatches
from statement_qa.synthetic import StatementSpec, build_specs, render_pdf
from statement_qa.synthetic.__main__ import main
from statement_qa.synthetic.render import BANNER
from statement_qa.synthetic.spec import (
    ELECTRICITY,
    LAST_DAY,
    PAYROLL,
    PHONE,
    RECURRING_DAYS,
    RENT,
    monthly_dates,
)

SPECS = build_specs()


def _id(spec: StatementSpec) -> str:
    return spec.expected.statement_id


@pytest.mark.parametrize(
    ("start", "end", "day", "expected"),
    [
        (dt.date(2026, 3, 1), dt.date(2026, 3, 31), 8, [dt.date(2026, 3, 8)]),
        (dt.date(2026, 3, 1), dt.date(2026, 3, 31), LAST_DAY, [dt.date(2026, 3, 31)]),
        (dt.date(2026, 2, 1), dt.date(2026, 2, 28), LAST_DAY, [dt.date(2026, 2, 28)]),
        (dt.date(2026, 4, 1), dt.date(2026, 4, 30), 31, [dt.date(2026, 4, 30)]),
        (
            dt.date(2025, 12, 15),
            dt.date(2026, 1, 14),
            LAST_DAY,
            [dt.date(2025, 12, 31)],
        ),
        (dt.date(2025, 12, 15), dt.date(2026, 1, 14), 1, [dt.date(2026, 1, 1)]),
        (dt.date(2025, 12, 15), dt.date(2026, 1, 14), 15, [dt.date(2025, 12, 15)]),
        (dt.date(2026, 3, 10), dt.date(2026, 3, 20), 8, []),
    ],
    ids=[
        "mid-month",
        "last-day",
        "february-end",
        "31st-in-april",
        "cross-year-last-day",
        "cross-year-1st",
        "cross-year-on-start",
        "outside-period",
    ],
)
def test_monthly_dates(
    start: dt.date, end: dt.date, day: int, expected: list[dt.date]
) -> None:
    assert monthly_dates(start, end, day) == expected


@pytest.mark.parametrize("spec", SPECS, ids=_id)
def test_bills_and_pay_recur_once_a_month_on_their_day(spec: StatementSpec) -> None:
    transactions = spec.expected.transactions
    counts = Counter(t.description for t in transactions)

    assert (counts[RENT], counts[ELECTRICITY], counts[PHONE], counts[PAYROLL]) == (
        1,
        1,
        1,
        2,
    )
    for description, days in RECURRING_DAYS.items():
        expected_dates = sorted(
            date
            for day in days
            for date in monthly_dates(
                spec.expected.period_start, spec.expected.period_end, day
            )
        )
        actual = sorted(t.date for t in transactions if t.description == description)
        assert actual == expected_dates


@pytest.mark.parametrize("spec", SPECS, ids=_id)
def test_both_paydays_pay_the_same_salary(spec: StatementSpec) -> None:
    pay = {t.amount for t in spec.expected.transactions if t.description == PAYROLL}

    assert len(pay) == 1


def test_overdrawn_statements_open_with_rent_and_go_below_zero() -> None:
    overdrawn = [
        s for s in SPECS if any(t.balance < 0 for t in s.expected.transactions)
    ]

    for spec in overdrawn:
        first = spec.expected.transactions[0]
        assert first.description == RENT
        assert first.balance < 0


@pytest.mark.parametrize("spec", SPECS, ids=_id)
def test_every_month_ends_in_credit(spec: StatementSpec) -> None:
    # Everyday spending is fitted to income, so even overdrawn months recover.
    assert spec.expected.closing_balance > 0


def test_same_seed_gives_the_same_specs() -> None:
    assert build_specs(7) == build_specs(7)
    assert build_specs(7) != build_specs(8)


def test_rendering_is_byte_for_byte_repeatable() -> None:
    assert render_pdf(SPECS[0]) == render_pdf(SPECS[0])


def test_statement_set_covers_the_plan() -> None:
    assert 5 <= len(SPECS) <= 10
    assert {spec.layout for spec in SPECS} == {"A", "B", "C"}
    assert len({_id(spec) for spec in SPECS}) == len(SPECS)


def test_some_statements_go_overdrawn() -> None:
    overdrawn = [
        s for s in SPECS if any(t.balance < 0 for t in s.expected.transactions)
    ]

    assert len(overdrawn) >= 2


def test_exactly_one_statement_does_not_reconcile() -> None:
    assert sum(bool(find_balance_mismatches(s.expected)) for s in SPECS) == 1


@pytest.mark.parametrize("spec", SPECS, ids=_id)
def test_rendered_pdf_has_two_to_four_pages_each_with_the_banner(
    spec: StatementSpec,
) -> None:
    reader = PdfReader(io.BytesIO(render_pdf(spec)))

    assert 2 <= len(reader.pages) <= 4
    assert len(reader.pages) == spec.expected.page_count
    for page in reader.pages:
        assert BANNER in page.extract_text()


def test_cli_writes_one_pdf_per_statement(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out_dir = tmp_path / "statements"

    exit_code = main(["--out", str(out_dir)])

    assert exit_code == 0
    assert sorted(p.name for p in out_dir.iterdir()) == sorted(
        f"{_id(spec)}.pdf" for spec in SPECS
    )
    assert "wrote 6 statements" in capsys.readouterr().out


def test_cli_requires_an_output_directory() -> None:
    with pytest.raises(SystemExit):
        main([])
