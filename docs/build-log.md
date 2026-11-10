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
