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
- **Plan changes I made:** chose no type checker for now (ruff only).
- **What Claude built:**
  - `backend/` as a uv project (`src/statement_qa`, Python 3.13).
  - `create_app()` factory with `GET /health` returning a Pydantic `HealthResponse`.
  - Ruff with type-hint (`ANN`) and security (`S`) rules.
  - `.github/workflows/backend.yml` running `uv sync --locked`, ruff check, ruff format check and pytest, with actions pinned to commit SHAs.
  - Dependencies: fastapi, pydantic and uvicorn at runtime; pytest, httpx2 and ruff for dev.
- **Mid-build change:** the planned `httpx` was swapped for `httpx2`, because Starlette 1.10 deprecates `httpx` for `TestClient`. Also noted: FastAPI 0.162 brings in `opentelemetry-api` transitively.
- **What I changed in review, and why:**
- **Tests:** 3 pytest tests for `/health` (status and body, 405 on POST, OpenAPI response model).
- **Time taken:**
