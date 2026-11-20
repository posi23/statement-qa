# Build log

One entry per milestone: what I asked Claude Code for, what it produced, and what I changed before merging.

## Template

### M#: title (PR link)

- **Asked for:**
- **Plan changes I made:**
- **What Claude built:**
- **What I changed in review, and why:**
- **Tests:**
- **Time taken:**

### M1: backend skeleton ([PR #1](https://github.com/posi23/statement-qa/pull/1))

- **Asked for:** a backend skeleton with uv, FastAPI, ruff, pytest and a GitHub Actions workflow, with every dependency listed before adding it.
- **Plan changes I made:** no type checker for now (ruff only). I took the recommendation to keep M1 to the tools PLAN.md names and to revisit once M2 adds real logic.
- **What Claude built:**
  - `backend/` as a uv project (`src/statement_qa`, Python 3.13).
  - `create_app()` factory with `GET /health` returning a Pydantic `HealthResponse`.
  - Ruff with type-hint (`ANN`) and security (`S`) rules.
  - `.github/workflows/backend.yml` running `uv sync --locked`, ruff check, ruff format check and pytest, with actions pinned to commit SHAs.
  - Dependencies: fastapi, pydantic and uvicorn at runtime; pytest, httpx2 and ruff for dev.
- **Mid-build change:** the planned `httpx` was swapped for `httpx2`, because Starlette 1.10 deprecates `httpx` for `TestClient`. Also noted: FastAPI 0.162 brings in `opentelemetry-api` transitively.
- **What I changed in review, and why:**
  - I approved swapping `httpx` for `httpx2` mid-build. Starlette 1.10 deprecates `httpx` for `TestClient`, and I didn't want a warning on every test run from day one.
  - I had both `review-pr` findings fixed before opening the PR, not after:
    - `persist-credentials: false` on checkout, so the CI token isn't left in `.git/config` for later steps.
    - Removed a schema test that only repeated the body check, so it couldn't fail on its own.
- **Tests:** 3 pytest tests for `/health` (status and body, 405 on POST, OpenAPI response model).
- **Time taken:** about 30 minutes from plan to open PR (planning began around 15:00, PR opened 15:29), plus review time before merge.

### M2: synthetic statements and parsing (PR link added when opened)

- **Asked for:** a generator for 5–10 fake statement PDFs (different layouts, 2–4 pages, some overdrawn) and a parser that turns each PDF into Pydantic `Transaction` rows with the page they came from. Generator first, then the parser, with the `write-tests` skill for the tests.
- **Plan changes I made:**
  - Approved `pypdf` (runtime) and `fpdf2` (dev only), the picks PLAN.md recommends, over `pdfplumber` and `reportlab`.
  - Asked what the PDFs are and whether they should be public. They're entirely invented, so they're committed, but every page now carries a `SYNTHETIC SAMPLE - NOT A REAL STATEMENT` banner so nobody mistakes one for a real document.
  - Asked for each step to be explained by following one concrete row through the code, instead of a box-and-arrow overview.
- **What Claude built:**
  - `statement_qa.synthetic`: `build_specs(seed)` makes 6 statements (3 layouts x 2), each with an `expected` `ParsedStatement` that serves as the answer key. `render_pdf` draws them with fpdf2. `python -m statement_qa.synthetic --out ...` writes them to `data/synthetic/`. Output is byte-identical between runs.
  - The three layouts differ in columns (Withdrawals/Deposits, signed Amount, Debit/Credit), date format (`2026-03-04`, `04 Mar 2026`, `Mar 04` with the year from the period) and how overdrafts print (`-24.20`, `24.20 OD`, `($24.20)`). One statement crosses the new year, and one has a deliberately misprinted balance.
  - `statement_qa.parsing`: pypdf reports each string with its x/y position. The parser groups strings into rows by y and assigns each one to the column whose header starts nearest. That's how a lone `80.00` is known to be a withdrawal, without guessing from the balance.
  - `find_balance_mismatches` compares each printed balance with opening balance plus amounts so far, so one typo is flagged once. M6's agent will reuse it.
- **Mid-build changes:**
  - Before writing the parser, a spike confirmed that pypdf gives usable positions for fpdf2 output, so `pdfplumber` wasn't needed.
  - The first generated overdrawn statement stayed below zero almost all month. A forced payday about a sixth of the way through now makes it dip and recover.
  - All generated amounts are rounded to two decimal places.
- **What I changed in review, and why:** (filled in after `review-pr`)
- **Tests:** 76 pytest runs (24 planned cases plus a banner check, many parametrized). Every generated statement parses back exactly, including pages; the committed PDFs match the generator; and there are unit tests for amounts, dates, layout, reconcile and error paths. No network, no model calls.
- **Known limit:** the summary parser expects the label and value as separate strings (`Opening balance:` then `10.00`), not one string `Opening balance: 10.00`.
- **Time taken:** planned Nov 10–11, built Nov 20 with pauses for explanations.
