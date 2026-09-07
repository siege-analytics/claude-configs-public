# Fixture — FAIL (default-deny proof)

Trivial-investigation with `repo-local-only` — a token PR A did not
anticipate. Must fail with the same allowlist diagnostic. Proves the
enforcement is an allowlist, not a denylist against the three known
invented tokens.

## Trivial-investigation declaration

Category: repo-local-only
Cannot produce error: All effects contained within the repo.
Evidence: `git diff --stat` shows only files inside the repo changed.
Falsification: If the change leaks outside the repo boundary.
