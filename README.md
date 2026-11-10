# statement-qa

Ask questions about bank statements and get answers that cite the page they came from.

Work in progress. See `docs/PLAN.md` for the build plan and `docs/build-log.md` for how each part was built.

## Stack

Python, FastAPI, LangChain, Claude, Postgres with pgvector, React with TypeScript.

## How I built this

I'm building this with Claude Code as my main tool:

- `CLAUDE.md` holds the project rules.
- `.claude/skills/` holds the two custom skills I use: `write-tests` and `review-pr`.
- Every milestone is planned first, built on its own branch and reviewed before merging.
- The build log records what I asked for and what I changed.

All data in this repo is synthetic.
