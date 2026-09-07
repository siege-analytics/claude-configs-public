# Fixture — FAIL (external-shape-modeling never-trivial across block types)

Trivial-change with a VALID Category token, but the diff touches
`scripts/discipline/check-trivial-claim.sh` — an external-shape-modeling
file. Must fail regardless of Category, with an external-shape-modeling
diagnostic. Proves the never-trivial trigger applies across ALL three
Trivial-* block types.

## Trivial-change declaration

Category: comments-only
Cannot produce error: Comment-only change.
Evidence: `git diff -G '^[^#/* ]'` returns empty.
Falsification: If a non-comment line is changed.
