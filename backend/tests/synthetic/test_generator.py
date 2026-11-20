"""Tests for the synthetic statement generator."""

import io
from pathlib import Path

import pytest
from pypdf import PdfReader

from statement_qa.parsing import find_balance_mismatches
from statement_qa.synthetic import StatementSpec, build_specs, render_pdf
from statement_qa.synthetic.__main__ import main
from statement_qa.synthetic.render import BANNER

SPECS = build_specs()


def _id(spec: StatementSpec) -> str:
    return spec.expected.statement_id


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
