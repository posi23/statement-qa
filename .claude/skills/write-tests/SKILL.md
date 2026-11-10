---
name: write-tests
description: Write pytest or Vitest tests for a module in this repo, covering the happy path, edge cases and failure paths, without any network calls. Use when a milestone adds or changes a module, or when asked to test something.
---

# Write tests

1. Read the module and list its public functions and the behaviour each one promises.
2. For each function, list the cases before writing anything:
   - the normal case
   - edge cases (empty input, one item, boundary dates, negative and zero amounts, overdrawn balances)
   - failure paths (bad input, missing data, a model reply that doesn't match the schema)
3. Show me the case list and wait for a go-ahead if there are more than 15 cases.
4. Write the tests:
   - Python: pytest, in `backend/tests/` mirroring the module path. Use LangChain's `FakeListChatModel` or `GenericFakeChatModel` for Claude and `DeterministicFakeEmbedding` for embeddings. No network, no real API keys.
   - TypeScript: Vitest, next to the file as `*.test.ts`. Mock `fetch`, never a real server.
   - Build test data with small factory functions. No real names or account numbers.
5. Run the tests and report pass/fail. If a test fails because the code is wrong, say so and don't change the code to make it pass without asking.
