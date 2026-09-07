# Fixture — FAIL

Trivial-investigation with `internal-refactor`. Must fail.

## Trivial-investigation declaration

Category: internal-refactor
Cannot produce error: Refactor is internal to a single module.
Evidence: `git diff --stat` shows only one module changed.
Falsification: If any external caller's behavior changes.
