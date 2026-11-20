"""Keep dev-only packages out of the code the app runs."""

import subprocess
import sys


def test_app_and_parser_do_not_load_the_dev_only_pdf_writer() -> None:
    # A fresh interpreter: this test session has already imported fpdf through
    # the generator tests, so checking sys.modules here would prove nothing.
    code = (
        "import sys, statement_qa.main, statement_qa.parsing; "
        "print('fpdf' in sys.modules)"
    )

    # Runs this venv's own Python with a fixed string, no outside input.
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == "False"
