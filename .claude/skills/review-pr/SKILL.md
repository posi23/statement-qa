---
name: review-pr
description: Review the current branch against main before a PR is opened. Reports findings ranked by severity and does not edit files. Use before opening or merging a PR.
---

# Review PR

1. Run `git diff main...HEAD` and read every changed file in full, not just the hunks.
2. Check, in this order:
   - **Correctness:** wrong results, unhandled errors, off-by-one dates, money handled as float instead of Decimal.
   - **Tests:** behaviour that changed without a test, and tests that would pass even if the code were wrong.
   - **Security:**
     - secrets in code or logs
     - SQL built with string formatting
     - statement text that can reach the model's instructions (prompt injection)
   - **LLM use:**
     - a missing step limit on tool loops
     - model output used without validating it against the Pydantic schema
     - real API calls in unit tests
   - **Rules:** anything that breaks CLAUDE.md, and new dependencies nobody approved.
3. Report findings most severe first. Give each one a file and line, a one-sentence problem, and a concrete failure case. Say plainly when there's nothing to report.
4. Don't edit files. I decide which findings to fix.
