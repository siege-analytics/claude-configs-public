# Fixture — FAIL (external-shape-modeling never-trivial)

Trivial-investigation with a VALID Category token, but the diff touches
`hooks/git/self-review.sh` — an external-shape-modeling file. Must fail
regardless of Category, with an external-shape-modeling diagnostic.

## Trivial-investigation declaration

Category: test-only
Cannot produce error: Adds a fixture only.
Evidence: `git diff --stat` shows one test file changed, 8 insertions.
Falsification: If a non-test file is modified.
