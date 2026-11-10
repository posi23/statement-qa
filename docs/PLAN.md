# Build plan

Each milestone is one branch and one PR. Start each one in Claude Code plan mode with the starter prompt, review the plan, then let it build. Read every diff before merging and log the milestone in `build-log.md`.

```
 PDF statements ──► parse rows ──► chunk + embed ──► pgvector (Postgres)
                        │                                  │
                        ▼                                  ▼
                 transactions table          question ──► retriever ──► Claude ──► answer + cited pages
                        │                                                 ▲
                        └──── sum_transactions tool (milestone 6) ────────┘
```

## Open decisions

| Decision | Recommendation | Alternative |
|---|---|---|
| Python tooling | uv (`brew install uv`) | pipenv |
| Embeddings | FastEmbed running locally (`BAAI/bge-small-en-v1.5`): no key, no cost | Voyage AI, which needs a key |
| PDF generation | fpdf2 | reportlab |
| PDF parsing | pypdf | pdfplumber, which handles tables better |

## M1: backend skeleton

- **Goal:** a FastAPI app with `GET /health`, ruff, pytest and a GitHub Actions workflow that runs both.
- **Done when:** CI is green on the PR and `CLAUDE.md` lists the commands.
- **Starter prompt:** "Read CLAUDE.md and docs/PLAN.md. Plan M1: the backend skeleton with uv, FastAPI, ruff, pytest and a GitHub Actions workflow. List every dependency you want before adding it."

## M2: synthetic statements and parsing

- **Goal:**
  - A script that generates 5–10 fake bank statement PDFs (different layouts, 2–4 pages each, some overdrawn balances) into `data/synthetic/`.
  - A parser that turns each PDF into Pydantic `Transaction` rows (date, description, amount, balance, page).
- **Done when:** the parser tests pass on every generated statement, including a statement whose running balance doesn't reconcile.
- **Starter prompt:** "Plan M2 from docs/PLAN.md. Generator first, then the parser. Use the write-tests skill for the parser."

## M3: ingest into pgvector

- **Goal:**
  - Docker Compose for Postgres with pgvector.
  - An ingest step that chunks each statement by page, embeds the chunks, and stores them with page and statement metadata (LangChain `PGVector`).
  - The parsed rows go into a plain `transactions` table.
- **Done when:** ingest is idempotent (running it twice doesn't duplicate anything) and the tests use fake embeddings.
- **Starter prompt:** "Plan M3. Explain the chunking choice and how re-ingesting stays idempotent before writing code."

## M4: ask endpoint

- **Goal:**
  - `POST /ask` takes a question.
  - The retriever pulls the top-k chunks, and Claude (LangChain `ChatAnthropic`) returns a Pydantic `Answer` with the answer text and a list of citations (statement and page).
  - Statement text sits in its own marked block in the prompt.
- **Done when:**
  - Tests cover a normal answer, an "I can't find that" answer, and a chunk that tries to inject instructions.
  - All tests use the fake chat model.
- **Starter prompt:** "Plan M4. Show me the prompt and the Answer schema before implementing."

## M5: evals

- **Goal:**
  - `evals/questions.yaml` holds 20–30 questions with expected answers and pages.
  - A runner calls the real API, scores answer correctness and citation accuracy, and records tokens and cost from `usage`.
- **Done when:** the README has a results table (accuracy, citation accuracy, cost per question) and the runner only runs by hand.
- **Starter prompt:** "Plan M5. Propose how to score free-text answers fairly before writing the runner."

## M6: agentic balance check

- **Goal:** Claude gets two tools through LangChain `bind_tools`:
  - `search_statement`
  - `sum_transactions(statement, start, end)`, which runs SQL over the `transactions` table

  It uses them to answer questions like "does the closing balance reconcile?". Tool choice stays on `auto`, since forced tool choice isn't supported on current models.
- **Done when:**
  - Tests drive the tool loop with a fake model that emits tool calls.
  - The loop has a step limit.
- **Starter prompt:** "Plan M6. Keep the agent loop small and explain the step limit and the error handling."

## M7: frontend

- **Goal:**
  - A React + TypeScript (Vite) page to ask a question and show the answer with clickable citations.
  - Zod validates the API response.
- **Done when:** Vitest covers the response parsing and the empty and error states, and CI runs it.
- **Starter prompt:** "Plan M7 for the frontend. Keep it to one page."

## M8: polish

- **Goal:**
  - A "How I built this" section in the README that links the build log and the skills.
  - A 5-minute recording of one Claude Code session (plan, build, review) linked from the README.
- **Done when:** someone new can clone the repo, run it, and see how it was built.
