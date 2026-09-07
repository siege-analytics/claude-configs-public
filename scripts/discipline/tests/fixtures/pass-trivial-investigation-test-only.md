# Fixture — PASS

Trivial-investigation with valid Category `test-only` and full evidence
chain. Must pass.

## Trivial-investigation declaration

Category: test-only
Cannot produce error: Adds a fixture case to an existing test file; no implementation touched.
Evidence: `git diff --stat` shows only tests/fixtures/new-case.md changed, 12 insertions.
Falsification: If a non-test file is modified, this declaration is wrong.
