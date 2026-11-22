"""Write the synthetic statements as PDFs.

uv run python -m statement_qa.synthetic --out ../data/synthetic
"""

import argparse
from collections.abc import Sequence
from pathlib import Path

from statement_qa.synthetic.render import render_pdf
from statement_qa.synthetic.spec import DEFAULT_SEED, build_specs


def main(argv: Sequence[str] | None = None) -> int:
    """Generate every statement into `--out` and return the exit code."""
    parser = argparse.ArgumentParser(
        prog="python -m statement_qa.synthetic",
        description="Generate synthetic bank statement PDFs.",
    )
    parser.add_argument(
        "--out", type=Path, required=True, help="directory to write PDFs into"
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="random seed")
    args = parser.parse_args(argv)

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    specs = build_specs(args.seed)
    for spec in specs:
        (out_dir / f"{spec.expected.statement_id}.pdf").write_bytes(render_pdf(spec))
    print(f"wrote {len(specs)} statements to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
