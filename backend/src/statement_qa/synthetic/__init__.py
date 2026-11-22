"""Generate synthetic bank statements for development and tests.

Everything here is invented. Rendering needs `fpdf2`, which is a dev
dependency, so nothing in the running app imports this package.
"""

from statement_qa.synthetic.render import render_pdf
from statement_qa.synthetic.spec import DEFAULT_SEED, StatementSpec, build_specs

__all__ = ["DEFAULT_SEED", "StatementSpec", "build_specs", "render_pdf"]
